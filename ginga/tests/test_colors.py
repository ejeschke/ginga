#
# Unit Tests for the colors.py functions
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import numpy as np

from ginga.colors import *

class TestError(Exception):
    pass


class TestColors(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger("TestColors")
		self.initial_color_list_length = len(color_list)

	def test_lookup_color_white_tuple(self):
		expected = (1.0, 1.0, 1.0)
		actual = lookup_color("white", "tuple")

		assert np.allclose(expected, actual)


	def test_lookup_color_black_tuple(self):
		expected = (0.0, 0.0, 0.0)
		actual = lookup_color("black", "tuple")

		assert np.allclose(expected, actual)

	def test_lookup_color_white_hash(self):
		expected = "#ffffff"
		actual = lookup_color("white", "hash")

		assert expected == actual


	def test_lookup_color_black_black(self):
		expected = "#000000"
		actual = lookup_color("black", "hash")

		assert expected == actual

	def test_lookup_color_yellow_tuple(self):
		expected = (1.0, 1.0, 0.0)
		actual = lookup_color("yellow")

		assert np.allclose(expected, actual)

	def test_lookup_color_raise_exception(self):
		self.assertRaises(ValueError, lookup_color, "white", "unknown_format")

	def tearDown(self):
		pass

if __name__ == '__main__':
    unittest.main()

#END