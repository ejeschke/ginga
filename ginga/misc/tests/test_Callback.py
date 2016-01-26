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

	def test_clear_callback_empties_list(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		test_callbacks.clear_callback("test_name")

		expected = 0
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

	def test_clear_callback_nonexistent_name(self):
		test_callbacks = Callback.Callbacks()

		assert "unknown_callback_key" not in test_callbacks.cb

		test_callbacks.clear_callback("unknown_callback_key")

		assert "unknown_callback_key" in test_callbacks.cb
		assert isinstance(test_callbacks.cb["unknown_callback_key"], list)

		expected = 0
		actual = len(test_callbacks.cb["unknown_callback_key"])
		assert expected == actual

	def test_enable_callback_nonexistent_name(self):
		test_callbacks = Callback.Callbacks()

		assert "unknown_callback_key" not in test_callbacks.cb

		test_callbacks.enable_callback("unknown_callback_key")

		assert "unknown_callback_key" in test_callbacks.cb
		assert isinstance(test_callbacks.cb["unknown_callback_key"], list)

		expected = 0
		actual = len(test_callbacks.cb["unknown_callback_key"])
		assert expected == actual

	def test_enable_callback_already_existent_name(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]

		assert "test_name" in test_callbacks.cb
		assert isinstance(test_callbacks.cb["test_name"], list)

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		test_callbacks.enable_callback("test_name")

		# testing that enable_callback() causes no change
		assert "test_name" in test_callbacks.cb
		assert isinstance(test_callbacks.cb["test_name"], list)

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

	def test_has_callback_existent_name(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]

		expected = True
		actual = test_callbacks.has_callback("test_name")
		assert expected == actual

	def test_has_callback_non_existent_name(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]

		expected = False
		actual = test_callbacks.has_callback("non_existent_name")
		assert expected == actual


	def test_has_callback_non_existent_name_empty_dict(self):
		test_callbacks = Callback.Callbacks()

		expected = False
		actual = test_callbacks.has_callback("non_existent_name")
		assert expected == actual

	def test_delete_callback_existent_name(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]
		assert "test_name" in test_callbacks.cb

		test_callbacks.delete_callback("test_name")
		assert "test_name" not in test_callbacks.cb
		
	def test_delete_callback_non_existent_name(self):
		test_callbacks = Callback.Callbacks()

		def test_callback_function():
			pass

		test_callbacks.cb["test_name"] = [(test_callbacks, (), {}),]

		self.assertRaises(
			Callback.CallbackError, 
			test_callbacks.delete_callback, 
			"non_existent_name"
		)


	def test_delete_callback_non_existent_name_empty_dict(self):
		test_callbacks = Callback.Callbacks()
		
		self.assertRaises(
			Callback.CallbackError, 
			test_callbacks.delete_callback, 
			"non_existent_name"
		)
	

	def test_add_callback(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.add_callback("test_name", test_callback_function)

		assert "test_name" in test_callbacks.cb

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = (test_callback_function, (), {})
		actual = test_callbacks.cb["test_name"][0]
		assert expected == actual

		def another_test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.add_callback("test_name", another_test_callback_function)

		expected = 2
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = (another_test_callback_function, (), {})
		actual = test_callbacks.cb["test_name"][1]
		assert expected == actual



	def test_add_callback_arguments(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.add_callback(
							"test_name", 
							test_callback_function,
							'test_arg_1',
							'test_arg_2',
							test_keyword_arg1 = "test",
							test_keyword_arg2 = "test"
						)

		assert "test_name" in test_callbacks.cb

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = 	(
						test_callback_function, 
						('test_arg_1', 'test_arg_2'), 
						{'test_keyword_arg1':'test', 'test_keyword_arg2':'test'}
					)
		actual = test_callbacks.cb["test_name"][0]
		assert expected == actual

	def test_set_callback(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.set_callback("test_name", test_callback_function)

		assert "test_name" in test_callbacks.cb

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = (test_callback_function, (), {})
		actual = test_callbacks.cb["test_name"][0]
		assert expected == actual

		def another_test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.set_callback("test_name", another_test_callback_function)

		expected = 2
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = (another_test_callback_function, (), {})
		actual = test_callbacks.cb["test_name"][1]
		assert expected == actual


	def test_set_callback_arguments(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			pass

		test_callbacks.set_callback(
							"test_name", 
							test_callback_function,
							'test_arg_1',
							'test_arg_2',
							test_keyword_arg1 = "test",
							test_keyword_arg2 = "test"
						)

		assert "test_name" in test_callbacks.cb

		expected = 1
		actual = len(test_callbacks.cb["test_name"])
		assert expected == actual

		expected = 	(
						test_callback_function, 
						('test_arg_1', 'test_arg_2'), 
						{'test_keyword_arg1':'test', 'test_keyword_arg2':'test'}
					)
		actual = test_callbacks.cb["test_name"][0]
		assert expected == actual

	def test_make_callback_non_existent_name(self):
		test_callbacks = Callback.Callbacks()

		expected = None
		actual = test_callbacks.make_callback("non_existent_event_name")

		assert expected == actual


	def test_make_callback_empty_callback_list(self):
		test_callbacks = Callback.Callbacks()

		test_callbacks.enable_callback("known_name")

		assert "known_name" in test_callbacks.cb

		expected = False
		actual = test_callbacks.make_callback("known_name")

		assert expected == actual


	def test_make_callback_single_callback_true(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			return True

		test_callbacks.add_callback("test_name", test_callback_function)

		assert "test_name" in test_callbacks.cb

		expected = True
		actual = test_callbacks.make_callback("test_name")
		assert expected == actual


	def test_make_callback_single_callback_false(self):
		test_callbacks = Callback.Callbacks()
		
		def test_callback_function(obj, *args, **kwargs):
			return False

		test_callbacks.add_callback("test_name", test_callback_function)

		assert "test_name" in test_callbacks.cb

		expected = False
		actual = test_callbacks.make_callback("test_name")
		assert expected == actual


	def tearDown(self):
		pass

if __name__ == '__main__':
    unittest.main()

#END
