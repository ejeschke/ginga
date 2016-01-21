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

	def tearDown(self):
		pass

if __name__ == '__main__':
    unittest.main()

#END