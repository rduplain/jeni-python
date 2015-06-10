import unittest

import jeni

from test_jeni import BasicInjector


class Python2AnnotationTestCase(unittest.TestCase):
    def test_annotate_without_annotations(self):
        def fn(hello):
            "unused"
        self.assertRaises(AttributeError, jeni.annotate, fn)


if __name__ == '__main__': unittest.main()
