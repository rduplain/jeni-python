import unittest

import jeni


class TestProviderBasics(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def get_x(self):
                return 6

            def get_y(self):
                return 7

        @Provider.annotate('x', 'y')
        def f(x, y, z=None):
            if z is not None:
                return x * y * z
            return x * y

        self.f = f
        self.provider = Provider()

    def test_call(self):
        self.assertEqual(42, self.f(6, 7))

    def test_apply(self):
        self.assertEqual(42, self.provider.apply(self.f))

    def test_partial(self):
        fn = self.provider.partial(self.f)
        self.assertEqual(42, fn())

    def test_partial_more(self):
        fn = self.provider.partial(self.f)
        self.assertEqual(4200, fn(100))
        self.assertEqual(4200, fn(z=100))


class TestProviderNotApplicable(unittest.TestCase):
    def setUp(self):
        self.provider = jeni.BaseProvider()

        def f(x, y):
            return x * y

        self.f = f

    def test_call(self):
        self.assertEqual(42, self.f(6, 7))

    def test_lookup_error_on_apply(self):
        self.assertRaises(LookupError, self.provider.apply, self.f)

    def test_lookup_error_on_partial(self):
        self.assertRaises(LookupError, self.provider.partial, self.f)


class TestProviderAccessByName(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def get_thing(self, name=None):
                if name is not None:
                    return "thing with name '{}'".format(name)
                return 'thing without a name'

        @Provider.annotate('thing')
        def f(thing):
            return thing

        @Provider.annotate('thing:foo')
        def g(thing):
            return thing

        self.f = f
        self.g = g
        self.provider = Provider()

    def test_noname(self):
        self.assertEqual('thing without a name', self.provider.apply(self.f))

    def test_name(self):
        self.assertEqual("thing with name 'foo'", self.provider.apply(self.g))


class TestProviderArguments(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def __init__(self, data):
                self.data = data

            def get_data(self, name=None):
                return self.data.get(name, jeni.UNSET)

        @Provider.annotate('data:x', 'data:y', fn='data:fn')
        def f(x, y, fn=None):
            if fn is None:
                fn = lambda *a: a
            return fn(x, y)

        self.f = f
        self.Provider = Provider

    def test_call(self):
        self.assertEqual((0, 1), self.f(0, 1))
        self.assertEqual(2, self.f(1, 1, fn=lambda *a: sum(a)))

    def test_unset_keyword(self):
        provider = self.Provider({'x': 0, 'y': 1})
        self.assertEqual((0, 1), provider.apply(self.f))

        another = self.Provider({'x': 1, 'y': 1, 'fn': lambda *a: sum(a)})
        self.assertEqual(2, another.apply(self.f))

    def test_unset_positional(self):
        provider = self.Provider({'y': 1})
        self.assertRaises(jeni.UnsetError, provider.apply, self.f)

        another = self.Provider({'y': 1, 'fn': lambda *a: sum(a)})
        self.assertRaises(jeni.UnsetError, another.apply, self.f)


class TestProviderCivics(unittest.TestCase):
    def setUp(self):
        class ProviderABC(jeni.BaseProvider):
            def get_a(self):
                return 2

            def get_b(self):
                return 4

            def get_c(self):
                return 8

            def get_fn(self):
                return lambda a, b, c: a * b * c

        self.ProviderABC = ProviderABC
        self.provider_abc = ProviderABC()

        class ProviderXYZ(jeni.BaseProvider):
            def get_x(self):
                return 98

            def get_y(self):
                return 99

            def get_z(self):
                return 100

            def get_fn(self):
                return lambda x, y, z: [x, y, z]

        self.ProviderXYZ = ProviderXYZ
        self.provider_xyz = ProviderXYZ()

        @ProviderABC.annotate('fn', 'a', 'b', 'c')
        @ProviderXYZ.annotate('fn', 'x', 'y', 'z')
        def g(fn, x, y, z):
            return fn(x, y, z)

        self.g = g

    def test_call(self):
        self.assertEqual(6, self.g(lambda *a: sum(a), 1, 2, 3))
        self.assertEqual(True, self.g(lambda *a: any(a), False, True, False))
        self.assertEqual(False, self.g(lambda *a: all(a), False, True, False))

    def test_apply(self):
        self.assertEqual(2 * 4 * 8, self.provider_abc.apply(self.g))
        self.assertEqual([98, 99, 100], self.provider_xyz.apply(self.g))

    def test_partial(self):
        abc = self.provider_abc.partial(self.g)
        self.assertEqual(2 * 4 * 8, abc())
        xyz = self.provider_xyz.partial(self.g)
        self.assertEqual([98, 99, 100], xyz())

    def test_extend(self):
        class Provider(jeni.BaseProvider):
            def get_fn(self):
                return lambda *a: sum(a)

        provider = Provider()
        provider.extend(self.provider_abc)
        self.assertRaises(LookupError, provider.apply, self.g)

        @Provider.annotate('fn', 'a', 'b', 'c')
        def do_g(*a):
            return self.g(*a)

        self.assertEqual(2 + 4 + 8, provider.apply(do_g))

    def test_extend_multiple(self):
        class Provider(jeni.BaseProvider):
            def get_fn(self):
                return lambda *a: sum(a)

        provider = Provider()
        provider.extend(self.provider_abc, self.provider_xyz)
        self.assertRaises(LookupError, provider.apply, self.g)

        @Provider.annotate('fn', 'a', 'b', 'z')
        def do_g(*a):
            return self.g(*a)

        self.assertEqual(2 + 4 + 100, provider.apply(do_g))

        base = jeni.BaseProvider()

        another = Provider()
        another.extend(base, self.provider_abc, self.provider_xyz)
        self.assertEqual(2 + 4 + 100, another.apply(do_g))

        yet_another = Provider()
        yet_another.extend(base)
        yet_another.extend(self.provider_abc)
        yet_another.extend(self.provider_xyz)
        self.assertEqual(2 + 4 + 100, yet_another.apply(do_g))

    def test_implement(self):
        class Provider(jeni.BaseProvider):
            def get_a(self):
                return 1010

            def get_b(self):
                return 2020

            def get_c(self):
                return 3030

            def get_fn(self):
                return lambda *a: sum(a)

        Provider.implement(self.ProviderABC)
        provider = Provider()
        self.assertEqual(1010 + 2020 + 3030, provider.apply(self.g))

    def test_implement_multiple(self):
        class BaseProvider(jeni.BaseProvider):
            def get_a(self):
                return 1010

            def get_b(self):
                return 2020

            def get_c(self):
                return 3030

            def get_x(self):
                return -3030

            def get_y(self):
                return -2020

            def get_z(self):
                return -1010

            def get_fn(self):
                return lambda *a: sum(a)

        class ProviderOne(BaseProvider):
            """Implements ABC then XYZ in one call."""

        ProviderOne.implement(self.ProviderABC, self.ProviderXYZ)
        provider_one = ProviderOne()
        self.assertEqual(1010 + 2020 + 3030, provider_one.apply(self.g))

        class ProviderTwo(BaseProvider):
            """Implements ABC then XYZ in separate calls."""

        ProviderTwo.implement(self.ProviderABC)
        ProviderTwo.implement(self.ProviderXYZ)
        provider_two = ProviderTwo()
        self.assertEqual(1010 + 2020 + 3030, provider_two.apply(self.g))

        class ProviderThree(BaseProvider):
            """Implements XYZ then ABC in one call."""

        ProviderThree.implement(self.ProviderXYZ, self.ProviderABC)
        provider_three = ProviderThree()
        self.assertEqual(-1010 + -2020 + -3030, provider_three.apply(self.g))

        class ProviderFour(BaseProvider):
            """Implements XYZ then ABC in separate call."""

        ProviderFour.implement(self.ProviderXYZ)
        ProviderFour.implement(self.ProviderABC)
        provider_four = ProviderFour()
        self.assertEqual(-1010 + -2020 + -3030, provider_four.apply(self.g))

        class ProviderFive(BaseProvider):
            """Implements Base then XYZ then ABC."""

        ProviderFive.implement(
            jeni.BaseProvider,
            self.ProviderXYZ,
            self.ProviderABC)
        provider_five = ProviderFive()
        self.assertEqual(-1010 + -2020 + -3030, provider_five.apply(self.g))


class CloseMe(object):
    def __init__(self):
        self.closed = None

    def open(self):
        self.closed = False

    def close(self):
        self.closed = True


class TestProviderSimpleClose(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def get_thing(self):
                if hasattr(self, 'thing'):
                    return self.thing
                self.thing = CloseMe()
                self.thing.open()
                return self.thing

            def close_thing(self):
                if not hasattr(self, 'thing'):
                    return
                self.thing.close()

        self.provider = Provider()

    def test_close(self):
        thing = self.provider.get_thing()
        thing2 = self.provider.get_thing()
        self.assertIs(thing, thing2)
        self.assertEqual(False, thing.closed)
        self.provider.close()
        self.assertEqual(True, thing.closed)

    def test_close_early(self):
        self.provider.close() # assert no error


class TestProviderCloseContext(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def get_thing(self):
                if hasattr(self, 'thing'):
                    return self.thing
                self.thing = CloseMe()
                self.thing.open()
                return self.thing

            def close_thing(self):
                if not hasattr(self, 'thing'):
                    return
                self.thing.close()

        self.Provider = Provider

    def test_close(self):
        with self.Provider() as provider:
            thing = provider.get_thing()
            thing2 = provider.get_thing()
            self.assertIs(thing, thing2)
            self.assertEqual(False, thing.closed)
        self.assertEqual(True, thing.closed)

    def test_close_early(self):
        with self.Provider():
            pass # assert no error

    def test_close_again(self):
        with self.Provider() as provider:
            pass # assert no error
        provider.close() # assert no error


class TestProviderCloseOrder(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            before_close = ['some_method', 'close_foo']

            def __init__(self):
                self.call_count = {}
                self.call_order = []

            def get_bar(self):
                if hasattr(self, 'bar'):
                    return self.bar
                self.bar = CloseMe()
                self.bar.open()
                return self.bar

            def close_bar(self):
                count = self.call_count.get('close_bar', 0)
                self.call_count['close_bar'] = count + 1
                self.call_order.append('close_bar')
                if not hasattr(self, 'bar'):
                    return
                self.bar.close()

            def get_foo(self):
                if hasattr(self, 'foo'):
                    return self.foo
                self.foo = CloseMe()
                self.foo.open()
                return self.foo

            def close_foo(self):
                count = self.call_count.get('close_foo', 0)
                self.call_count['close_foo'] = count + 1
                self.call_order.append('close_foo')
                if not hasattr(self, 'foo'):
                    return
                self.foo.close()

            def some_method(self):
                count = self.call_count.get('some_method', 0)
                self.call_count['some_method'] = count + 1
                self.call_order.append('some_method')

        self.Provider = Provider
        self.provider = Provider()

    def test_close(self):
        foo = self.provider.get_foo()
        foo2 = self.provider.get_foo()
        self.assertIs(foo, foo2)
        bar = self.provider.get_bar()
        bar2 = self.provider.get_bar()
        self.assertIs(bar, bar2)
        self.assertEqual(False, foo.closed)
        self.assertEqual(False, bar.closed)
        self.assertIsNot(foo, bar)

        self.provider.close()

        self.assertEqual(True, foo.closed)
        self.assertEqual(True, bar.closed)
        self.assertEqual(1, self.provider.call_count['close_foo'])
        self.assertEqual(1, self.provider.call_count['close_bar'])
        self.assertEqual(1, self.provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order, self.provider.call_order)

    def test_close_unused(self):
        foo = self.provider.get_foo()
        self.assertEqual(False, foo.closed)

        self.provider.close()

        self.assertEqual(True, foo.closed)
        self.assertEqual(1, self.provider.call_count['close_foo'])
        self.assertEqual(1, self.provider.call_count['close_bar'])
        self.assertEqual(1, self.provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order, self.provider.call_order)

    def test_close_early(self):
        self.provider.close()
        self.assertEqual(1, self.provider.call_count['close_foo'])
        self.assertEqual(1, self.provider.call_count['close_bar'])
        self.assertEqual(1, self.provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order, self.provider.call_order)

    def test_close_again(self):
        self.provider.close()
        self.provider.close()
        self.assertEqual(2, self.provider.call_count['close_foo'])
        self.assertEqual(2, self.provider.call_count['close_bar'])
        self.assertEqual(2, self.provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order * 2, self.provider.call_order)

    def test_context_manager(self):
        del self.provider # do not confuse instances in test

        with self.Provider() as provider:
            foo = provider.get_foo()
            bar = provider.get_bar()
            self.assertEqual(False, foo.closed)
            self.assertEqual(False, bar.closed)
            self.assertIsNot(foo, bar)

        self.assertEqual(True, foo.closed)
        self.assertEqual(True, bar.closed)
        self.assertEqual(1, provider.call_count['close_foo'])
        self.assertEqual(1, provider.call_count['close_bar'])
        self.assertEqual(1, provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order, provider.call_order)

    def test_duplicate_before(self):
        self.Provider.before_close = [
            'some_method',
            'close_foo',
            'some_method']
        self.provider.close()
        self.assertEqual(1, self.provider.call_count['close_foo'])
        self.assertEqual(1, self.provider.call_count['close_bar'])
        self.assertEqual(1, self.provider.call_count['some_method'])
        call_order = ['some_method', 'close_foo', 'close_bar']
        self.assertEqual(call_order, self.provider.call_order)


class TestCloseExtend(unittest.TestCase):
    def setUp(self):
        class FooProvider(jeni.BaseProvider):
            def get_foo(self):
                if hasattr(self, 'foo'):
                    return self.foo
                self.foo = CloseMe()
                self.foo.open()
                return self.foo

            def close_foo(self):
                if not hasattr(self, 'foo'):
                    return
                self.foo.close()

        class BarProvider(jeni.BaseProvider):
            def get_bar(self):
                if hasattr(self, 'bar'):
                    return self.bar
                self.bar = CloseMe()
                self.bar.open()
                return self.bar

            def close_bar(self):
                if not hasattr(self, 'bar'):
                    return
                self.bar.close()

        self.FooProvider = FooProvider
        self.BarProvider = BarProvider

    def test_close(self):
        foo_provider = self.FooProvider()
        foo = foo_provider.get_foo()
        self.assertEqual(False, foo.closed)

        bar_provider = self.BarProvider()
        bar_provider.extend(foo_provider)
        bar = bar_provider.get_bar()

        @self.BarProvider.annotate('foo', 'bar')
        def baz(foo, bar):
            self.assertEqual(False, foo.closed)
            self.assertEqual(False, bar.closed)

        bar_provider.apply(baz)
        bar_provider.close()
        self.assertEqual(False, foo.closed)
        self.assertEqual(True, bar.closed)

        foo_provider.close()
        self.assertEqual(True, foo.closed)
        self.assertEqual(True, bar.closed)

    def test_close_immediately(self):
        foo_provider = self.FooProvider()
        bar_provider = self.BarProvider()
        bar_provider.extend(foo_provider)

        # Assert no error.
        foo_provider.close()
        bar_provider.close()


class TestSelfApply(unittest.TestCase):
    def setUp(self):
        class BaseProvider(jeni.BaseProvider):
            def get_x(self):
                return 6

            def get_y(self):
                return 7

        class Provider(BaseProvider):
            @BaseProvider.annotate('x', 'y')
            def calculate_z(self, x, y):
                return x * y

            def get_z(self):
                return self.apply(self.calculate_z)

        @Provider.annotate('z', 'y', 'x')
        def f(z, y, x):
            return z * y * x

        self.f = f
        self.provider = Provider()

    def test_call(self):
        self.assertEqual(42, self.provider.calculate_z(6, 7))

    def test_direct_apply(self):
        self.assertEqual(42, self.provider.apply(self.provider.calculate_z))

    def test_indirect_apply(self):
        self.assertEqual(42 * 7 * 6, self.provider.apply(self.f))


class TestConstructorAnnotation(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            def get_x(self):
                return 6

            def get_y(self):
                return 7

        @Provider.annotate('x', 'y')
        class Point(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

            def as_tuple(self):
                return self.x, self.y

        self.Point = Point
        self.provider = Provider()

    def test_call(self):
        point = self.Point(-1, 1)
        self.assertEqual((-1, 1), point.as_tuple())

    def test_apply(self):
        point = self.provider.apply(self.Point)
        self.assertIsInstance(point, self.Point)
        self.assertEqual((6, 7), point.as_tuple())

    def test_partial(self):
        create_point = self.provider.partial(self.Point)
        point = create_point()
        self.assertIsInstance(point, self.Point)
        self.assertEqual((6, 7), point.as_tuple())


class TestCustomMethodNames(unittest.TestCase):
    def setUp(self):
        class Provider(jeni.BaseProvider):
            accessor_pattern = '{}_gimme'

            def __init__(self):
                self.x = CloseMe()

            def x_gimme(self):
                self.x.open()
                return self.x

            def x_go_away(self):
                self.x.close()

            def is_close_method(self, name):
                return name.endswith('_go_away')

        @Provider.annotate('x')
        def f(x):
            self.assertEqual(False, x.closed)
            return x

        self.Provider = Provider
        self.provider = Provider()
        self.f = f

    def test_apply(self):
        x = self.provider.apply(self.f)
        self.assertEqual(x, self.provider.x)

    def test_close(self):
        x = self.provider.apply(self.f)
        self.provider.close()
        self.assertIs(True, x.closed)

    def test_format_method(self):
        class ImpatientProvider(self.Provider):
            def provide_y_now(self):
                return 'y'

            def format_accessor_name(self, object_name):
                return 'provide_{}_now'.format(object_name)

        @ImpatientProvider.annotate('y')
        def g(y):
            return y

        provider = ImpatientProvider()
        self.assertEqual('y', provider.apply(g))


if __name__ == '__main__':
    unittest.main()
