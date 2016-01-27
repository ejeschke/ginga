#
# Unit Tests for the Future class
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import numpy as np

import ginga.misc.Future as gingaMisc


class TestError(Exception):
    pass


class TestFuture(unittest.TestCase):

    def setUp(self):
        pass

    def test_init(self):
        test_future = gingaMisc.Future()

        assert hasattr(test_future, 'cb')
        assert test_future.res == None
        assert test_future.data == None
        assert 'resolved' in test_future.cb

        expected = []
        actual = test_future.cb['resolved']
        assert expected == actual

    def test_init_with_data(self):
        test_future = gingaMisc.Future("TestData")

        assert hasattr(test_future, 'cb')
        assert test_future.res == None
        assert test_future.data == "TestData"
        assert 'resolved' in test_future.cb

        expected = []
        actual = test_future.cb['resolved']
        assert expected == actual

    def test_get_data_no_data(self):
        test_future = gingaMisc.Future()

        expected = None
        actual = test_future.get_data()
        assert expected == actual

    def test_get_data_some_data(self):
        test_future = gingaMisc.Future("TestData")

        expected = "TestData"
        actual = test_future.get_data()
        assert expected == actual

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# END
