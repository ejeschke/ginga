#
# Unit Tests for the Callbacks class
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import numpy as np

import ginga.misc.Callback as Callback


class TestError(Exception):
    pass


class TestCallbacks(unittest.TestCase):
	def setUp(self):
		pass

	def test_init(self):
		test_callbacks = Callback.Callbacks()

		assert isinstance(test_callbacks.cb, dict)

		expected = 0
		actual = len(test_callbacks.cb)
		assert expected == actual

		expected = {}
		actual = test_callbacks.cb
		assert expected == actual
		
	def tearDown(self):
		pass

if __name__ == '__main__':
    unittest.main()

#END
