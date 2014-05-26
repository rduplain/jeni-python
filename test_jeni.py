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


@BasicInjector.provider('answer')
def answer():
    yield 42


@BasicInjector.provider('spam', name=True)
def spam():
    try:
        count_str = yield 'spam'
        while True:
            count_str = yield 'spam' * int(count_str)
    finally:
        pass


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
        self.assertEqual('Hello, world!', self.injector.resolve('hello'))
        self.assertEqual('Hello, world!', self.injector.resolve('hello'))
        self.assertEqual('Hello, thing!', self.injector.resolve('hello:thing'))
        self.assertEqual('Hello, thing!', self.injector.resolve('hello:thing'))

    def test_factory(self):
        self.assertEqual('eggs!', self.injector.resolve('eggs'))
        self.assertEqual('eggs!', self.injector.resolve('eggs'))

        # This factory does not accept name.
        self.assertRaises(TypeError, self.injector.resolve, 'eggs:thing')

    def test_generator(self):
        self.assertEqual(42, self.injector.resolve('answer'))
        self.assertEqual(42, self.injector.resolve('answer'))

        # This generator does not accept name.
        self.assertRaises(TypeError, self.injector.resolve, 'answer:thing')

    def test_generator_with_name(self):
        self.assertEqual('spam', self.injector.resolve('spam'))
        self.assertEqual('spam', self.injector.resolve('spam'))
        self.assertEqual('spamspam', self.injector.resolve('spam:2'))
        self.assertEqual('spamspamspam', self.injector.resolve('spam:3'))
        self.assertEqual('spamspamspamspam', self.injector.resolve('spam:4'))
        self.assertEqual('spam', self.injector.resolve('spam'))

        self.assertRaises(ValueError, self.injector.resolve, 'spam:forty')
        self.assertEqual('spam', self.injector.resolve('spam'))

    def test_not_registered(self):
        self.assertRaises(LookupError, self.injector.resolve, 'nothing')

    def test_provider_class_registration(self):
        class SubInjector(BasicInjector):
            pass
        SubInjector.provider('hello2', HelloProvider)
        injector = SubInjector()
        self.assertEqual('Hello, world!', injector.resolve('hello2'))
        self.assertEqual('Hello, world!', injector.resolve('hello'))

    def test_factory_registration(self):
        class SubInjector(BasicInjector):
            pass
        SubInjector.factory('eggs2', eggs)
        injector = SubInjector()
        self.assertEqual('eggs!', injector.resolve('eggs2'))
        self.assertEqual('eggs!', injector.resolve('eggs'))


class SubInjectorTestCase(BasicInjectorTestCase):
    def setUp(self):
        self.injector = SubInjector()

    def test_generator(self):
        self.assertEqual('No one knows.', self.injector.resolve('answer'))
        self.assertEqual('No one knows.', self.injector.resolve('answer'))

        # This generator does not accept name.
        self.assertRaises(TypeError, self.injector.resolve, 'answer:thing')


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
        self.assertEqual(('spam eggs!'), injector.resolve('dish'))
        self.assertEqual(('spam eggs! eel'), injector.resolve('dish:eel'))

    def test_annotated_generator(self):
        class Injector(BasicInjector):
            pass
        @Injector.provider('spammish')
        @jeni.annotate('spam')
        def generator(spam):
            yield spam
        injector = Injector()
        self.assertEqual('spam', injector.resolve('spammish'))


@BasicInjector.factory('error')
def error():
    raise jeni.UnsetError


@jeni.annotate('error')
def unset_arg(unused):
    raise RuntimeError('UnsetError should raise before this on apply.')


@jeni.annotate('hello', unused='error')
def unset_kwarg(hello, unused=None):
    return unused


class UnsetArgumentTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_unset_arg(self):
        self.assertRaises(RuntimeError, unset_arg, None)
        self.assertRaises(jeni.UnsetError, self.injector.apply, unset_arg)

    def test_unset_kwarg(self):
        self.assertIs(None, self.injector.apply(unset_kwarg))


class CloseMe(object):
    def __init__(self):
        self.closed = None

    def open(self):
        self.closed = False

    def close(self):
        self.closed = True


class CloseTestInjector(jeni.Injector):
    pass


@CloseTestInjector.provider('via_class')
class ClosingProvider(jeni.Provider):
    def __init__(self):
        self.thing = CloseMe()

    def get(self):
        if self.thing.closed is None:
            self.thing.open()
        return self.thing

    def close(self):
        self.thing.close()


@CloseTestInjector.provider('via_generator')
def closing_generator():
    thing = CloseMe()
    thing.open()
    yield thing
    thing.close()


@CloseTestInjector.provider('via_generator_with_name', name=True)
def closing_generator_with_name():
    # Name is not actually used, but generator accepts name.
    try:
        thing = CloseMe()
        thing.open()
        yield thing
        while True:
            yield thing
    finally:
        thing.close()


class ClosingTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = CloseTestInjector()

    def test_multiple_close(self):
        self.injector.close()
        self.assertRaises(RuntimeError, self.injector.close)
        self.assertRaises(RuntimeError, self.injector.close)

    def assert_with_note(self, note):
        thing = self.injector.resolve(note)
        self.assertIs(thing, self.injector.resolve(note))
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


class TestGeneratorProvider(unittest.TestCase):
    def test_generator(self):
        def fn():
            yield 42
        provider = jeni.GeneratorProvider(fn)
        provider.init()
        self.assertEqual(42, provider.get())
        self.assertEqual(42, provider.get())
        self.assertRaises(TypeError, provider.get, name='name')

    def test_init_error(self):
        def fn():
            "unused"
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
        self.assertEqual('Hello, world!', self.injector.resolve(note))

    def test_tuple(self):
        note = ('hello', 'name')
        self.Injector.provider(note, HelloProvider)
        self.assertEqual('Hello, name!', self.injector.resolve(note))

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

    @unittest.skip('TODO: classmethod support')
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


class TestClassInProgress(unittest.TestCase):
    def test_class_in_progress(self):
        class Dummy(object):
            self.assertTrue(jeni.class_in_progress())

    def test_class_not_in_progress(self):
        self.assertFalse(jeni.class_in_progress())

    def test_broken_stack(self):
        stack = [(None, None, None, None, None, None)]
        self.assertFalse(jeni.class_in_progress(stack=stack))


if __name__ == '__main__':
    unittest.main()
