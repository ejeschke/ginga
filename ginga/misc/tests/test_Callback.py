"""Unit Tests for the Callbacks class."""

import pytest

import ginga.misc.Callback as Callback


class TestCallbacks:

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

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]

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

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]

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

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]

        expected = True
        actual = test_callbacks.has_callback("test_name")
        assert expected == actual

    def test_has_callback_non_existent_name(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function():
            pass

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]

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

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]
        assert "test_name" in test_callbacks.cb

        test_callbacks.delete_callback("test_name")
        assert "test_name" not in test_callbacks.cb

    def test_delete_callback_non_existent_name(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function():
            pass

        test_callbacks.cb["test_name"] = [(test_callbacks, (), {}), ]

        with pytest.raises(Callback.CallbackError):
            test_callbacks.delete_callback("non_existent_name")

    def test_delete_callback_non_existent_name_empty_dict(self):
        test_callbacks = Callback.Callbacks()

        with pytest.raises(Callback.CallbackError):
            test_callbacks.delete_callback("non_existent_name")

    def test_add_callback(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            pass

        test_callbacks.enable_callback("test_name")
        assert "test_name" in test_callbacks.cb

        test_callbacks.add_callback("test_name", test_callback_function)

        expected = 1
        actual = len(test_callbacks.cb["test_name"])
        assert expected == actual

        expected = (test_callback_function, (), {})
        actual = test_callbacks.cb["test_name"][0]
        assert expected == actual

        def another_test_callback_function(obj, *args, **kwargs):
            pass

        test_callbacks.add_callback(
            "test_name", another_test_callback_function)

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

        test_callbacks.enable_callback("test_name")
        assert "test_name" in test_callbacks.cb

        test_callbacks.add_callback(
            "test_name",
            test_callback_function,
            'test_arg_1',
            'test_arg_2',
            test_keyword_arg1="test",
            test_keyword_arg2="test"
        )

        assert "test_name" in test_callbacks.cb

        expected = 1
        actual = len(test_callbacks.cb["test_name"])
        assert expected == actual

        expected = (
            test_callback_function,
            ('test_arg_1', 'test_arg_2'),
            {'test_keyword_arg1': 'test', 'test_keyword_arg2': 'test'}
        )
        actual = test_callbacks.cb["test_name"][0]
        assert expected == actual

    def test_add_callback_exception(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            pass

        with pytest.raises(Callback.CallbackError):
            test_callbacks.add_callback("test_name", test_callback_function)

    def test_replace_callback(self):
        test_callbacks = Callback.Callbacks()
        test_callbacks.enable_callback("test_name")
        fired = []

        def first(obj, *args, **kwargs):
            fired.append('first')

        def second(obj, *args, **kwargs):
            fired.append('second')

        test_callbacks.replace_callback("test_name", first)
        test_callbacks.replace_callback("test_name", second)

        assert len(test_callbacks.cb["test_name"]) == 1
        test_callbacks.make_callback("test_name")
        assert fired == ['second']

    def test_replace_callback_enables_an_unknown_name(self):
        test_callbacks = Callback.Callbacks()

        def a_callback(obj, *args, **kwargs):
            pass

        test_callbacks.replace_callback("test_name", a_callback)

        assert "test_name" in test_callbacks.cb
        assert test_callbacks.cb["test_name"] == [(a_callback, (), {})]

    def test_replace_callback_takes_arguments(self):
        test_callbacks = Callback.Callbacks()
        test_callbacks.enable_callback("test_name")
        seen = []

        def a_callback(obj, *args, **kwargs):
            seen.append((args, kwargs))

        test_callbacks.replace_callback("test_name", a_callback, 'x', k=1)
        test_callbacks.make_callback("test_name")

        assert seen == [(('x',), {'k': 1})]

    def test_replace_callback_replaces_a_fresh_callable(self):
        """The case it is for.  add_callback will not register the same
        callback twice, but it compares the callable, and a lambda is a new
        object on every call -- so adding one repeatedly accumulates them.
        """
        test_callbacks = Callback.Callbacks()
        test_callbacks.enable_callback("test_name")
        fired = []

        for n in range(3):
            test_callbacks.add_callback(
                "test_name", lambda obj, n=n: fired.append(n))
        test_callbacks.make_callback("test_name")
        assert fired == [0, 1, 2], "add_callback accumulates them"

        fired[:] = []
        for n in range(3):
            test_callbacks.replace_callback(
                "test_name", lambda obj, n=n: fired.append(n))
        test_callbacks.make_callback("test_name")
        assert fired == [2], "replace_callback keeps only the last"

    def test_replace_callback_leaves_a_block_alone(self):
        """A block belongs to whoever set it up.  clear_callback resets the
        block state along with the handlers, which would unblock a callback
        someone else is suppressing and leave their count negative on the
        way out.
        """
        test_callbacks = Callback.Callbacks()
        test_callbacks.enable_callback("test_name")
        fired = []

        def a_callback(obj, *args, **kwargs):
            fired.append(1)

        test_callbacks.block_callback("test_name")
        test_callbacks.replace_callback("test_name", a_callback)

        assert test_callbacks._cb_block["test_name"]['count'] == 1
        test_callbacks.make_callback("test_name")
        assert fired == [], "still blocked"

        test_callbacks.unblock_callback("test_name")
        test_callbacks.make_callback("test_name")
        assert fired == [1]

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

        test_callbacks.set_callback(
            "test_name", another_test_callback_function)

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
            test_keyword_arg1="test",
            test_keyword_arg2="test"
        )

        assert "test_name" in test_callbacks.cb

        expected = 1
        actual = len(test_callbacks.cb["test_name"])
        assert expected == actual

        expected = (
            test_callback_function,
            ('test_arg_1', 'test_arg_2'),
            {'test_keyword_arg1': 'test', 'test_keyword_arg2': 'test'}
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

        test_callbacks.set_callback("test_name", test_callback_function)

        expected = True
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

    def test_make_callback_single_callback_false(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            return False

        test_callbacks.set_callback("test_name", test_callback_function)

        expected = False
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

    def test_make_callback_multiple_callback_all_true(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            return True

        def another_test_callback_function(obj, *args, **kwargs):
            return True

        test_callbacks.set_callback("test_name", test_callback_function)
        test_callbacks.set_callback(
            "test_name", another_test_callback_function)

        expected = True
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

    def test_make_callback_multiple_callback_some_true(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            return False

        def another_test_callback_function(obj, *args, **kwargs):
            return True

        test_callbacks.set_callback("test_name", test_callback_function)
        test_callbacks.set_callback(
            "test_name", another_test_callback_function)

        expected = True
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

    def test_make_callback_multiple_callback_all_false(self):
        test_callbacks = Callback.Callbacks()

        def test_callback_function(obj, *args, **kwargs):
            return False

        def another_test_callback_function(obj, *args, **kwargs):
            return False

        test_callbacks.set_callback("test_name", test_callback_function)
        test_callbacks.set_callback(
            "test_name", another_test_callback_function)

        expected = False
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

    def test_make_callback_raises_no_exception(self, capsys):
        test_callbacks = Callback.Callbacks()

        # This function when used as a callback should raise a TypeError
        # as the callbacks, from the logic in ginga.misc.Callback.Callbacks
        # always take the calling object as the first argument
        def test_callback_function():
            return True

        test_callbacks.set_callback("test_name", test_callback_function)

        # Checking that the callback eats up the TypeError exception
        expected = False
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

        captured = capsys.readouterr()
        assert 'Error making callback' in captured.out

    def test_make_callback_raises_no_exception_completes_all_callbacks(self, capsys):
        test_callbacks = Callback.Callbacks()

        def test_callback_function():
            return True

        def another_test_callback_function(obj, *args, **kwargs):
            return True

        test_callbacks.set_callback("test_name", test_callback_function)
        test_callbacks.set_callback(
            "test_name", another_test_callback_function)

        # Checking that the callback eats up the TypeError exception and
        # continues to the other callback and returns True in the end
        expected = True
        actual = test_callbacks.make_callback("test_name")
        assert expected == actual

        captured = capsys.readouterr()
        assert 'Error making callback' in captured.out

# END
