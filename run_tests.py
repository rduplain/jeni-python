# Run

import sys
import unittest

import test_jeni
try:
    unittest.main(module=test_jeni)
except SystemExit:
    pass

if sys.version_info >= (3,):
    import test_jeni_python3
    unittest.main(module=test_jeni_python3)
