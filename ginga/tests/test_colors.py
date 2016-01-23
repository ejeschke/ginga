#
# Unit Tests for the colors.py functions
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import numpy as np

import ginga.colors


class TestError(Exception):
    pass


class TestColors(unittest.TestCase):
	def setUp(self):
		self.logger = logging.getLogger("TestColors")
		self.color_list_length = len(ginga.colors.color_dict)

	# Tests for the lookup_color() funtion

	def test_lookup_color_white_tuple(self):
		expected = (1.0, 1.0, 1.0)
		actual = ginga.colors.lookup_color("white", "tuple")
		assert np.allclose(expected, actual)

	def test_lookup_color_black_tuple(self):
		expected = (0.0, 0.0, 0.0)
		actual = ginga.colors.lookup_color("black", "tuple")
		assert np.allclose(expected, actual)

	def test_lookup_color_white_hash(self):
		expected = "#ffffff"
		actual = ginga.colors.lookup_color("white", "hash")
		assert expected == actual

	def test_lookup_color_black_black(self):
		expected = "#000000"
		actual = ginga.colors.lookup_color("black", "hash")
		assert expected == actual

	def test_lookup_color_yellow_tuple(self):
		expected = (1.0, 1.0, 0.0)
		actual = ginga.colors.lookup_color("yellow")
		assert np.allclose(expected, actual)

	def test_lookup_color_unknown(self):
		self.assertRaises(KeyError, ginga.colors.lookup_color, "unknown_color")

	def test_lookup_color_raise_exception_unknown_key(self):
		self.assertRaises(KeyError, ginga.colors.lookup_color, "unknown_key")

	def test_lookup_color_raise_exception_unknown_format(self):
		self.assertRaises(ValueError, ginga.colors.lookup_color, "white", "unknown_format")


	# Tests for the get_colors() function
	def test_get_colors_len(self):
		expected = self.color_list_length
		actual = len(ginga.colors.get_colors())
		assert expected == actual

	def test_add_and_get_colors_len(self):
		ginga.colors.add_color("test_color_white", (0.0, 0.0, 0.0))

		expected = self.color_list_length + 1
		actual = len(ginga.colors.get_colors())
		assert expected == actual

		ginga.colors.remove_color("test_color_white")



	# Tests for the add_color() and remove_color() function

	def test_add_and_remove_color_len(self):
		ginga.colors.add_color("test_color_white", (0.0, 0.0, 0.0))

		expected = self.color_list_length + 1
		actual = len(ginga.colors.color_dict)
		assert expected == actual

		expected = len(ginga.colors.color_dict)
		actual = len(ginga.colors.color_list)
		assert expected == actual

		ginga.colors.remove_color("test_color_white")

		expected = self.color_list_length
		actual = len(ginga.colors.color_dict)
		assert expected == actual

		expected = len(ginga.colors.color_dict)
		actual = len(ginga.colors.color_list)
		assert expected == actual


	def test_add_and_remove_color_rbg(self):
		ginga.colors.add_color("test_color_white", (0.0, 0.0, 0.0))

		expected = (0.0, 0.0, 0.0)
		actual = ginga.colors.lookup_color("test_color_white")
		assert np.allclose(expected, actual)

		ginga.colors.remove_color("test_color_white")
		self.assertRaises(KeyError, ginga.colors.remove_color, "test_color_white")


	def test_add_color_wrong_rbg_type(self):
		self.assertRaises(TypeError, ginga.colors.add_color, "white", "string_wrong_format")

	def test_add_color_wrong_rbg_values(self):
		self.assertRaises(ValueError, ginga.colors.add_color, "test_color", (-1.0, 0.0, 0.0))

	def test_add_color_wrong_tuple_length(self):
		self.assertRaises(ValueError, ginga.colors.add_color, "test_color", (0.0, 0.0))

	def test_remove_color_unknown(self):
		self.assertRaises(KeyError, ginga.colors.remove_color, "unknown_color")


	# Tests for recalc_color_list() function

	def test_recalc_color_list(self):
		ginga.colors.color_dict["test_color_white"] = (0.0, 0.0, 0.0)

		expected = len(ginga.colors.color_dict) - 1 
		actual = len(ginga.colors.color_list)
		assert expected == actual

		ginga.colors.recalc_color_list()

		expected = len(ginga.colors.color_dict)
		actual = len(ginga.colors.color_list)
		assert expected == actual

		del ginga.colors.color_dict["test_color_white"]

		expected = len(ginga.colors.color_dict) + 1
		actual = len(ginga.colors.color_list)
		assert expected == actual

		ginga.colors.recalc_color_list()

		expected = len(ginga.colors.color_dict)
		actual = len(ginga.colors.color_list)
		assert expected == actual

	# Tests for scan_rgbtxt_buf() function
	
	def test_scan_rgbtxt_buf(self):
		test_rgb_lines = '''
			255 255 255		white
			0   0   0		black
			255   0   0		red
			0 255	  0		green
			0   0 255		blue
		'''

		result = ginga.colors.scan_rgbtxt_buf(test_rgb_lines)

		assert isinstance(result, dict)

		expected = 5
		actual = len(result)
		assert expected == actual

		expected = (1.0, 1.0, 1.0)
		actual = result["white"]
		assert np.allclose(expected, actual)


	def tearDown(self):
		pass

if __name__ == '__main__':
    unittest.main()

#END