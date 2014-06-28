import unittest

import jeni


class BasicInjector(jeni.Injector):
    pass


@BasicInjector.provider('hello')
class HelloProvider(jeni.Provider):
    def get(self, name=None):
        if name is None:
            name = 'world'
        return 'Hello, {}!'.format(name)


@BasicInjector.factory('eggs')
def eggs():
    return 'eggs!'


@BasicInjector.factory('echo')
def echo(name=None):
    return name


BasicInjector.value('zero', 0)


@BasicInjector.provider('answer')
def answer():
    yield 42


@BasicInjector.provider('spam', name=True)
def spam():
    count_str = yield 'spam'
    while True:
        count_str = yield 'spam' * int(count_str)


class SubInjector(BasicInjector):
    pass


@SubInjector.provider('answer')
def sub_answer():
    yield 'No one knows.'


class BoringInjector(jeni.Injector):
    pass


@BoringInjector.factory('hello')
@BoringInjector.factory('eggs')
@BoringInjector.factory('answer')
@BoringInjector.factory('spam')
def be_boring(name=None):
    if name is None:
        name = 'this injector'
    return '{} is boring'.format(name)


class BasicInjectorTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_provider_class(self):
        self.assertEqual('Hello, world!', self.injector.get('hello'))
        self.assertEqual('Hello, world!', self.injector.get('hello'))
        self.assertEqual('Hello, thing!', self.injector.get('hello:thing'))
        self.assertEqual('Hello, thing!', self.injector.get('hello:thing'))

    def test_factory(self):
        self.assertEqual('eggs!', self.injector.get('eggs'))
        self.assertEqual('eggs!', self.injector.get('eggs'))

        # This factory does not accept name.
        self.assertRaises(TypeError, self.injector.get, 'eggs:thing')

    def test_factory_with_name(self):
        self.assertEqual(None, self.injector.get('echo'))
        self.assertEqual('foo', self.injector.get('echo:foo'))

    def test_value(self):
        self.assertEqual(0, self.injector.get('zero'))
        self.assertEqual(0, self.injector.get('zero'))

        # This does not accept name.
        self.assertRaises(TypeError, self.injector.get, 'zero:thing')

    def test_generator(self):
        self.assertEqual(42, self.injector.get('answer'))
        self.assertEqual(42, self.injector.get('answer'))

        # This generator does not accept name.
        self.assertRaises(TypeError, self.injector.get, 'answer:thing')

    def test_generator_with_name(self):
        self.assertEqual('spam', self.injector.get('spam'))
        self.assertEqual('spam', self.injector.get('spam'))
        self.assertEqual('spamspam', self.injector.get('spam:2'))
        self.assertEqual('spamspamspam', self.injector.get('spam:3'))
        self.assertEqual('spamspamspamspam', self.injector.get('spam:4'))
        self.assertEqual('spam', self.injector.get('spam'))

        self.assertRaises(ValueError, self.injector.get, 'spam:forty')
        self.assertEqual('spam', self.injector.get('spam'))

    def test_not_registered(self):
        self.assertRaises(LookupError, self.injector.get, 'nothing')

    def test_provider_class_registration(self):
        class SubInjector(BasicInjector):
            pass
        SubInjector.provider('hello2', HelloProvider)
        injector = SubInjector()
        self.assertEqual('Hello, world!', injector.get('hello2'))
        self.assertEqual('Hello, world!', injector.get('hello'))

    def test_factory_registration(self):
        class SubInjector(BasicInjector):
            pass
        SubInjector.factory('eggs2', eggs)
        injector = SubInjector()
        self.assertEqual('eggs!', injector.get('eggs2'))
        self.assertEqual('eggs!', injector.get('eggs'))


class SubInjectorTestCase(BasicInjectorTestCase):
    def setUp(self):
        self.injector = SubInjector()

    def test_generator(self):
        self.assertEqual('No one knows.', self.injector.get('answer'))
        self.assertEqual('No one knows.', self.injector.get('answer'))

        # This generator does not accept name.
        self.assertRaises(TypeError, self.injector.get, 'answer:thing')


class BasicInjectorAnnotationTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()
        @jeni.annotate('hello', 'hello:x', 'eggs', 'answer', 'spam', 'spam:2')
        def fn(hello, hello_x, eggs, answer, spam, spam2):
            self.assertEqual('Hello, world!', hello)
            self.assertEqual('Hello, x!', hello_x)
            self.assertEqual('eggs!', eggs)
            self.assertEqual(42, answer)
            self.assertEqual('spam', spam)
            self.assertEqual('spamspam', spam2)
            return 0
        self.fn = fn

    def test_apply(self):
        self.assertEqual(0, self.injector.apply(self.fn))

    def test_partial(self):
        fn = self.injector.partial(self.fn)
        self.assertEqual(0, fn())

    def test_not_registered(self):
        @jeni.annotate('hello', 'nothing')
        def fn(hello, nothing):
            raise RuntimeError('UnsetError should raise before this on apply.')
        self.assertRaises(RuntimeError, fn, 'hello', None)
        self.assertRaises(LookupError, self.injector.apply, fn)

    def test_no_annotation(self):
        def fn():
            "unused"
        self.assertRaises(AttributeError, self.injector.apply, fn)

    def test_annotate_without_annotations(self):
        def fn(hello):
            "unused"
        self.assertRaises(AttributeError, jeni.annotate, fn)
        fn.__annotations__ = {}
        self.assertRaises(AttributeError, jeni.annotate, fn)

        fn.__annotations__ = {'hello': 'hello:world'}
        jeni.annotate(fn)
        self.assertTrue(jeni.annotate.has_annotations(fn))


class SubInjectorAnnotationTestCase(BasicInjectorAnnotationTestCase):
    def setUp(self):
        self.injector = SubInjector()
        @jeni.annotate('hello', 'hello:x', 'eggs', 'answer', 'spam', 'spam:2')
        def fn(hello, hello_x, eggs, answer, spam, spam2):
            self.assertEqual('Hello, world!', hello)
            self.assertEqual('Hello, x!', hello_x)
            self.assertEqual('eggs!', eggs)
            self.assertEqual('No one knows.', answer)
            self.assertEqual('spam', spam)
            self.assertEqual('spamspam', spam2)
            return 0
        self.fn = fn


class BoringAnnotationTestCase(BasicInjectorAnnotationTestCase):
    def setUp(self):
        self.injector = BoringInjector()
        @jeni.annotate('hello', 'hello:x', 'eggs', 'answer', 'spam', 'spam:2')
        def fn(hello, hello_x, eggs, answer, spam, spam2):
            self.assertEqual('this injector is boring', hello)
            self.assertEqual('x is boring', hello_x)
            self.assertEqual('this injector is boring', eggs)
            self.assertEqual('this injector is boring', answer)
            self.assertEqual('this injector is boring', spam)
            self.assertEqual('2 is boring', spam2)
            return 0
        self.fn = fn


class ApplyScenariosTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

        @jeni.annotate('hello')
        def fn_annotated(hello, *a, **kw):
            return hello, a, kw
        self.fn_annotated = fn_annotated

        def fn_not_annotated(*a, **kw):
            return a, kw
        self.fn_not_annotated = fn_not_annotated

    def test_apply(self):
        self.assertEqual(
            ('Hello, world!', (), {}),
            self.injector.apply(self.fn_annotated))
        self.assertRaises(
            AttributeError,
            self.injector.apply, self.fn_not_annotated)

    def test_additional_arguments_apply(self):
        self.assertEqual(
            ('Hello, world!', ('a', 'b'), {'letter': 'c'}),
            self.injector.apply(self.fn_annotated, 'a', 'b', letter='c'))
        self.assertRaises(
            AttributeError,
            self.injector.apply, self.fn_not_annotated, 'a', 'b', letter='c')

    def test_apply_regardless(self):
        self.assertEqual(
            ('Hello, world!', (), {}),
            self.injector.apply_regardless(self.fn_annotated))
        self.assertEqual(
            ((), {}),
            self.injector.apply_regardless(self.fn_not_annotated))

    def test_additional_arguments_apply_regardless(self):
        self.assertEqual(
            ('Hello, world!', ('a', 'b'), {'letter': 'c'}),
            self.injector.apply_regardless(
                self.fn_annotated, 'a', 'b', letter='c'))
        self.assertEqual(
            (('a', 'b'), {'letter': 'c'}),
            self.injector.apply_regardless(
                self.fn_not_annotated, 'a', 'b', letter='c'))

    def test_partial(self):
        self.assertEqual(
            ('Hello, world!', (), {}),
            self.injector.partial(self.fn_annotated)())
        self.assertRaises(
            AttributeError,
            self.injector.partial, self.fn_not_annotated)

    def test_additional_arguments_partial(self):
        self.assertEqual(
            ('Hello, world!', ('a', 'b'), {'letter': 'c'}),
            self.injector.partial(self.fn_annotated, 'a', 'b', letter='c')())
        self.assertRaises(
            AttributeError,
            self.injector.partial, self.fn_not_annotated, 'a', 'b', letter='c')

    def test_partial_regardless(self):
        self.assertEqual(
            ('Hello, world!', (), {}),
            self.injector.partial_regardless(self.fn_annotated)())
        self.assertEqual(
            ((), {}),
            self.injector.partial_regardless(self.fn_not_annotated)())

    def test_additional_arguments_partial_regardless(self):
        self.assertEqual(
            ('Hello, world!', ('a', 'b'), {'letter': 'c'}),
            self.injector.partial_regardless(
                self.fn_annotated, 'a', 'b', letter='c')())
        self.assertEqual(
            (('a', 'b'), {'letter': 'c'}),
            self.injector.partial_regardless(
                self.fn_not_annotated, 'a', 'b', letter='c')())


@jeni.annotate('spam', 'eggs')
def spam_eggs(spam, eggs, name=None):
    if name is not None:
        return ' '.join((spam, eggs, name))
    return ' '.join((spam, eggs))


class AnnotatedProviderTestCase(unittest.TestCase):
    def test_spam_eggs(self):
        class Injector(BasicInjector):
            pass
        Injector.factory('dish', spam_eggs)
        injector = Injector()
        self.assertEqual(('spam eggs!'), injector.get('dish'))
        self.assertEqual(('spam eggs! eel'), injector.get('dish:eel'))

    def test_annotated_generator(self):
        class Injector(BasicInjector):
            pass
        @Injector.provider('spammish')
        @jeni.annotate('spam')
        def generator(spam):
            yield spam
        injector = Injector()
        self.assertEqual('spam', injector.get('spammish'))


class MaybeTestCase(unittest.TestCase):
    def setUp(self):
        self.note = jeni.maybe('the_real_note')

    def test_maybe(self):
        self.assertEqual((jeni.MAYBE, 'the_real_note'), self.note)


class PartialNoteTestCase(unittest.TestCase):
    def setUp(self):
        self.fn = lambda: None
        self.note = jeni.partial(self.fn)

    def test_partial(self):
        self.assertEqual((jeni.PARTIAL, self.fn), self.note)


@BasicInjector.factory('error')
def error():
    raise jeni.UnsetError


@jeni.annotate('error')
def unset_arg(unused):
    raise RuntimeError('UnsetError should raise before this on apply.')


@jeni.annotate('hello', unused='error')
def unset_kwarg(hello, unused=None):
    raise RuntimeError('UnsetError should raise before this on apply.')


@jeni.annotate('hello', unused=jeni.annotate.maybe('error'))
def unset_maybe_kwarg(hello, unused=None):
    return unused


class UnsetArgumentTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_unset_arg(self):
        self.assertRaises(RuntimeError, unset_arg, None)
        self.assertRaises(jeni.UnsetError, self.injector.apply, unset_arg)

    def test_unset_kwarg(self):
        self.assertRaises(RuntimeError, unset_kwarg, None)
        self.assertRaises(jeni.UnsetError, self.injector.apply, unset_kwarg)

    def test_unset_maybe_kwarg(self):
        self.assertIs(None, self.injector.apply(unset_maybe_kwarg))


@jeni.annotate('hello:partial')
def hello_partial(hello):
    return hello


@jeni.annotate('hello:again', jeni.annotate.partial(hello_partial))
def hello_again_partial(hello, fn):
    return hello, fn()


class InjectPartialTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_partial_injection(self):
        self.assertEqual(
            ('Hello, again!', 'Hello, partial!'),
            self.injector.apply(hello_again_partial))


class CloseMe(object):
    # List of all closed instances for use in test inspection.
    closed_items = []

    def __init__(self, note):
        self.closed = None
        self.note = note

    def open(self):
        self.closed = False

    def close(self):
        assert not self.closed, '{!r} already closed'.format(self)
        self.closed_items.append(self)
        self.closed = True


class CloseTestInjector(jeni.Injector):
    pass


@CloseTestInjector.provider('via_class')
class ClosingProvider(jeni.Provider):
    def __init__(self):
        self.thing = CloseMe('via_class')

    def get(self):
        if self.thing.closed is None:
            self.thing.open()
        return self.thing

    def close(self):
        self.thing.close()


@CloseTestInjector.provider('via_generator')
def closing_generator():
    thing = CloseMe('via_generator')
    thing.open()
    yield thing
    thing.close()


@CloseTestInjector.provider('via_generator_with_name', name=True)
def closing_generator_with_name():
    # Name is not actually used, but generator accepts name.
    try:
        thing = CloseMe('via_generator_with_name')
        thing.open()
        yield thing
        while True:
            yield thing
    finally:
        thing.close()


@CloseTestInjector.provider('unset')
class UnsetProvider(jeni.Provider):
    def __init__(self):
        self.thing = CloseMe('unset')

    def get(self):
        raise jeni.UnsetError()

    def close(self):
        assert False, 'This should not be called by injector.'


CloseTestInjector.factory('echo', echo)


class ClosingTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = CloseTestInjector()

    def test_multiple_close(self):
        self.injector.close()
        self.assertRaises(RuntimeError, self.injector.close)
        self.assertRaises(RuntimeError, self.injector.close)

    def assert_with_note(self, note):
        thing = self.injector.get(note)
        self.assertIs(thing, self.injector.get(note))
        self.assertEqual(False, thing.closed)
        self.injector.close()
        self.assertEqual(True, thing.closed)

    def test_close_via_class(self):
        self.assert_with_note('via_class')

    def test_close_via_generator(self):
        self.assert_with_note('via_generator')

    def test_close_via_generator_with_name(self):
        self.assert_with_note('via_generator_with_name')

    def test_close_via_generator_with_name_name(self):
        self.assert_with_note('via_generator_with_name:name')

    def _test_close_order(self):
        injector = CloseTestInjector()
        num_prev_closed_items = len(CloseMe.closed_items)
        notes = ['via_generator', 'via_class', 'via_generator_with_name']
        close_order = list(reversed(notes))
        injector.get('echo') # Add a non-closing provider for good measure.
        for note in notes:
            injector.get(note)
        injector.get('via_class') # Get again; should not impact order.
        injector.close()
        self.assertEqual(
            close_order,
            [x.note for x in CloseMe.closed_items[num_prev_closed_items:]])

    def test_close_order(self):
        # Test multiple times given failed test is random order.
        for x in range(100):
            self._test_close_order()

    def test_unset_not_closed(self):
        # Verify that close test fires assertion.
        asserted = False
        try:
            provider = UnsetProvider()
            provider.close()
        except AssertionError:
            asserted = True
        assert asserted, 'UnsetProvider.close assertion not caught'

        self.assertRaises(jeni.UnsetError, self.injector.get, 'unset')
        self.injector.close()

    def test_cannot_get_after_close(self):
        self.assertEqual('thing', self.injector.get('echo:thing'))
        self.injector.close()
        self.assertRaises(RuntimeError, self.injector.get, 'echo:thing')


class InjectorStatsTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_empty_stats(self):
        self.assertEqual({}, self.injector.stats)

    def test_a_few_calls(self):
        stats = {
            'hello': 1,
            'hello:thing': 1,
            'eggs': 2,
        }
        self.injector.get('eggs')
        self.injector.get('hello')
        self.injector.get('hello:thing')
        self.injector.get('eggs')
        self.assertEqual(stats, self.injector.stats)

    def test_many_calls(self):
        stats = {
            'hello': 10,
            'hello:thing': 15,
            'eggs': 21,
        }
        for _ in range(10):
            self.injector.get('hello')
        for _ in range(21):
            self.injector.get('eggs')
        for _ in range(15):
            self.injector.get('hello:thing')
        self.assertEqual(stats, self.injector.stats)


class ContextManagerTestCase(unittest.TestCase):
    def test_with_block(self):
        with CloseTestInjector() as injector:
            thing = injector.get('via_class')
            self.assertEqual(False, thing.closed)
        self.assertEqual(True, thing.closed)

    def test_enter_exit(self):
        injector = CloseTestInjector().enter()
        thing = injector.get('via_class')
        self.assertEqual(False, thing.closed)
        injector.exit()
        self.assertEqual(True, thing.closed)


class TestGeneratorProvider(unittest.TestCase):
    def test_generator(self):
        def fn():
            yield 42
        provider = jeni.GeneratorProvider(fn)
        provider.init()
        self.assertEqual(42, provider.get())
        self.assertEqual(42, provider.get())
        self.assertRaises(TypeError, provider.get, name='name')

    def test_construction_error(self):
        def fn():
            "not a generator"
        self.assertRaises(TypeError, jeni.GeneratorProvider, fn)

    def test_init_error(self):
        def fn(): yield
        provider = jeni.GeneratorProvider(fn)
        self.assertRaises(RuntimeError, provider.get)
        self.assertRaises(RuntimeError, provider.close)

    def test_init_no_error(self):
        def fn():
            yield 42
        provider = jeni.GeneratorProvider(fn)
        provider.init()
        provider.get()
        provider.close()

    def test_unyielding_generator(self):
        def fn(work=False):
            if work:
                yield 'foo'
        self.assertEqual(['foo'], list(fn(work=True)))
        provider = jeni.GeneratorProvider(fn)
        self.assertRaises(RuntimeError, provider.init)

    def test_generator_with_broken_name_support(self):
        def fn():
            yield 42
        provider = jeni.GeneratorProvider(fn, support_name=True)
        provider.init()
        self.assertEqual(42, provider.get())
        self.assertRaises(RuntimeError, provider.get, name='name')

    def test_generator_which_keeps_yielding(self):
        def fn():
            yield 'one'; yield 'two'
        provider = jeni.GeneratorProvider(fn)
        provider.init()
        self.assertRaises(RuntimeError, provider.close)


class NonStringNoteTestCase(unittest.TestCase):
    class TestInjector(jeni.Injector):
        pass

    def setUp(self):
        self.Injector = self.TestInjector
        self.injector = self.Injector()

    def test_object(self):
        note = object()
        self.Injector.provider(note, HelloProvider)
        self.assertEqual('Hello, world!', self.injector.get(note))

    def test_tuple(self):
        note = ('hello', 'name')
        self.Injector.provider(note, HelloProvider)
        self.assertEqual('Hello, name!', self.injector.get(note))

    def test_tuple_too_small(self):
        note = ('hello',)
        self.assertRaises(
            ValueError, self.Injector.provider, note, HelloProvider)

    def test_tuple_too_large(self):
        note = ('hello', 'name', 'bogus')
        self.assertRaises(
            ValueError, self.Injector.provider, note, HelloProvider)


class MoreAnnotationTests(unittest.TestCase):
    def test_multiple_annotations(self):
        @jeni.annotate('foo', 'bar')
        def fn(foo, bar):
            "unused"
        decorator = jeni.annotate('baz', 'quux')
        self.assertRaises(AttributeError, decorator, fn)

    def test_method_annotation(self):
        class X(object):
            @jeni.annotate('spam', 'eggs')
            def eat(self, spam, eggs):
                return spam + eggs
        injector = BasicInjector()
        x = X()
        self.assertEqual('spameggs!', injector.apply(x.eat))

    def test_classmethod_annotation(self):
        class X(object):
            @jeni.annotate('spam', 'eggs')
            @classmethod
            def eat(cls, spam, eggs):
                return spam + eggs
        injector = BasicInjector()
        self.assertEqual('spameggs!', injector.apply(X.eat))


class TestBrokenProvider(unittest.TestCase):
    class TestInjector(jeni.Injector):
        pass

    def setUp(self):
        self.Injector = self.TestInjector
        self.injector = self.Injector()

    def decorate(self):
        @self.Injector.provider('no get')
        class BadProvider(object):
            pass

    def subclass(self):
        class BadSubclass(jeni.Provider):
            pass
        return BadSubclass

    def test_interface_check(self):
        self.assertRaises(ValueError, self.decorate)

    def test_subclass_meta(self):
        cls = self.subclass()
        self.assertRaises(TypeError, cls)


class TestInjectorProxy(unittest.TestCase):
    def setUp(self):
        self.x = jeni.InjectorProxy(BasicInjector())

    def test_getattr(self):
        self.assertEqual('Hello, world!', self.x.hello)
        self.assertEqual('Hello, thing!', getattr(self.x, 'hello:thing'))

    def test_unset_getattr(self):
        def _test():
            self.x.error
        self.assertRaises(jeni.UnsetError, _test)

    def test_getitem(self):
        self.assertEqual('Hello, world!', self.x['hello'])
        self.assertEqual('Hello, thing!', self.x['hello:thing'])

    def test_unset_getitem(self):
        def _test():
            self.x['error']
        self.assertRaises(jeni.UnsetError, _test)

    def test_in(self):
        self.assertIn('hello', self.x)
        self.assertIn('hello:thing', self.x)

    def test_not_in(self):
        self.assertNotIn('nothing', self.x)

    def test_not_in_when_unset(self):
        self.assertNotIn('error', self.x)
        class SubInjector(BasicInjector):
            pass
        @SubInjector.factory('picky')
        def no_spam(name=None):
            if name and 'spam' in name:
                raise jeni.UnsetError
            elif name:
                return name
            else:
                return "I don't like spam!"
        x = jeni.InjectorProxy(SubInjector())
        self.assertIn('picky', x)
        self.assertIn('picky:foo', x)
        self.assertNotIn('picky:spamspamspam', x)

    def test_class(self):
        self.assertRaises(TypeError, jeni.InjectorProxy, BasicInjector)


class TestClassInProgress(unittest.TestCase):
    def test_class_in_progress(self):
        class Dummy(object):
            self.assertTrue(jeni.class_in_progress())

    def test_class_not_in_progress(self):
        self.assertFalse(jeni.class_in_progress())

    def test_broken_stack(self):
        stack = [(None, None, None, None, None, None)]
        self.assertFalse(jeni.class_in_progress(stack=stack))


class TestIsCallable(unittest.TestCase):
    def test_annotate(self):
        self.assertTrue(jeni.is_callable(jeni.annotate))

    def test_lambda(self):
        self.assertTrue(jeni.is_callable(lambda: None))

    def test_object_type_and_instance(self):
        self.assertTrue(jeni.is_callable(object))
        self.assertFalse(jeni.is_callable(object()))


if __name__ == '__main__': unittest.main()
