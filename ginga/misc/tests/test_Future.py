#
# Unit Tests for the Future class
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import threading
import time

import ginga.misc.Future as gingaMisc


class TestError(Exception):
    pass


class TestFuture(unittest.TestCase):

    def setUp(self):
        pass

    def test_init(self):
        test_future = gingaMisc.Future()

        assert hasattr(test_future, 'cb')
        assert isinstance(test_future.evt, threading._Event)
        assert test_future.evt.isSet() == False
        assert test_future.res == None
        assert test_future.data == None
        assert 'resolved' in test_future.cb

        expected = []
        actual = test_future.cb['resolved']
        assert expected == actual

    def test_init_with_data(self):
        test_future = gingaMisc.Future("TestData")

        assert hasattr(test_future, 'cb')
        assert isinstance(test_future.evt, threading._Event)
        assert test_future.evt.isSet() == False
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

        test_future.freeze(
            test_method, "arg1", "arg2", kwarg1="test", kwarg2="test")

        assert test_future.method == test_method
        assert test_future.args == ("arg1", "arg2")
        assert test_future.kwdargs == {"kwarg1": "test", "kwarg2": "test"}

    def test_freeze_empty_args(self):
        test_future = gingaMisc.Future("TestData")

        def test_method():
            pass

        test_future.freeze(test_method)

        assert test_future.method == test_method
        assert test_future.args == ()
        assert test_future.kwdargs == {}

    def test_thaw_suppress_exception_no_exception(self):
        test_future = gingaMisc.Future("TestData")

        def test_method(*args, **kwargs):
            return True

        test_future.freeze(test_method)

        expected = True
        actual = test_future.thaw()
        assert expected == actual

        assert test_future.res == True
        assert test_future.evt.isSet() == True

    def test_thaw_suppress_exception_exception(self):
        test_future = gingaMisc.Future("TestData")

        def test_method():
            return True

        test_future.freeze(
            test_method, "arg1", "arg2", kwarg1="test", kwarg2="test")

        test_result = test_future.thaw()

        assert isinstance(test_result, TypeError)

        assert isinstance(test_future.res, TypeError)
        assert test_future.evt.isSet() == True

    def test_thaw_not_suppress_exception_no_exception(self):
        test_future = gingaMisc.Future("TestData")

        def test_method(*args, **kwargs):
            return True

        test_future.freeze(test_method)

        expected = True
        actual = test_future.thaw(False)
        assert expected == actual

        assert test_future.res == True
        assert test_future.evt.isSet() == True

    def test_thaw_not_suppress_exception_raise_exception(self):
        test_future = gingaMisc.Future("TestData")

        def test_method():
            return True

        test_future.freeze(
            test_method, "arg1", "arg2", kwarg1="test", kwarg2="test")

        self.assertRaises(TypeError, test_future.thaw, False)

        assert test_future.res == None
        assert test_future.evt.isSet() == False

    def test_has_value_unset(self):
        test_future = gingaMisc.Future("TestData")

        expected = False
        actual = test_future.has_value()
        assert expected == actual

    def test_has_value_set(self):
        test_future = gingaMisc.Future("TestData")

        test_future.evt.set()

        expected = True
        actual = test_future.has_value()
        assert expected == actual

    def test_resolve(self):
        test_future = gingaMisc.Future("TestData")

        test_future.resolve(True)

        assert test_future.res == True
        assert test_future.evt.isSet() == True

    def test_resolve_callback(self):
        test_future = gingaMisc.Future("TestData")

        def test_callback(obj):
            try:
                obj.res = not obj.res
            except:
                pass

        test_future.add_callback('resolved', test_callback)

        test_future.resolve(True)

        # Callback reverses the boolean 'res' value
        assert test_future.res == False
        assert test_future.evt.isSet() == True

    def test_wait(self):
        test_future = gingaMisc.Future("TestData")

        def test_method(*args, **kwargs):
            time.sleep(2)
            return True

        test_future.freeze(test_method)

        future_thread = threading.Thread(target=test_future.thaw)
        future_thread.start()

        expected = True
        actual = test_future.wait()
        assert expected == actual

    def test_wait_timeout(self):
        test_future = gingaMisc.Future("TestData")

        def test_method(*args, **kwargs):
            time.sleep(2)
            return True

        test_future.freeze(test_method)

        future_thread = threading.Thread(target=test_future.thaw)
        future_thread.start()

        self.assertRaises(gingaMisc.TimeoutError, test_future.wait, 1)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# END
