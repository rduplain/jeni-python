import unittest

import jeni

from test_jeni import BasicInjector


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
