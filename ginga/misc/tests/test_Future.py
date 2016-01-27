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

    def test_freeze(self):
    	test_future = gingaMisc.Future("TestData")

    	def test_method(*args, **kwargs):
    		pass

    	test_future.freeze(test_method, "arg1", "arg2", kwarg1="test", kwarg2="test")

    	assert test_future.method == test_method
    	assert test_future.args == ("arg1", "arg2")
    	assert test_future.kwdargs == {"kwarg1":"test", "kwarg2":"test"}

    def test_freeze_empty_args(self):
    	test_future = gingaMisc.Future("TestData")

    	def test_method():
    		pass

    	test_future.freeze(test_method)

    	assert test_future.method == test_method
    	assert test_future.args == ()
    	assert test_future.kwdargs == {}

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# END
