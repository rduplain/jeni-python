import unittest

import jeni

from test_jeni import BasicInjector


class Python3AnnotationTestCase(unittest.TestCase):
    def test_annotate_without_annotations(self):
        def fn(hello):
            "unused"
        jeni.annotate(fn)
        self.assertTrue(jeni.annotate.has_annotations(fn))

    def test_annotate_without_dunder_annotations(self):
        # Unclear when this would come up; testing it given Python 2 support.
        class NoDunderAnnotations(object):
            def __getattr__(self, name):
                if name == '__annotations__':
                    raise AttributeError()
                return super().__getattr__(name)

            def __call__(self):
                "unused"

        fn = NoDunderAnnotations()
        self.assertTrue(hasattr(fn, '__call__'))
        self.assertFalse(hasattr(fn, '__annotations__'))
        self.assertFalse(hasattr(fn, 'fake')) # coverage
        with self.assertRaises(AttributeError):
            jeni.annotate(fn)


@jeni.annotate
def annotated_function(hello: 'hello:thing', eggs: 'eggs'):
    return hello, eggs


class FunctionAnnotationTestCase(unittest.TestCase):
    def setUp(self):
        self.injector = BasicInjector()

    def test_function_annotation(self):
        self.assertEqual(
            ('Hello, thing!', 'eggs!'),
            self.injector.apply(annotated_function))


if __name__ == '__main__': unittest.main()
