import unittest
import ginga

def ginga_test_suite():
	loader = unittest.TestLoader()
	suite = loader.discover('ginga')
	return suite
