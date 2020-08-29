"""Unit Tests for the colors.py functions"""

import logging

import pytest
from numpy.testing import assert_allclose

import ginga.colors


class TestColors(object):
    def setup_class(self):
        self.logger = logging.getLogger("TestColors")
        self.color_list_length = len(ginga.colors.color_dict)

    # Tests for the lookup_color() funtion

    @pytest.mark.parametrize(
        ('input_color', 'format', 'expected'),
        [("white", "tuple", (1.0, 1.0, 1.0)),
         ("black", "tuple", (0.0, 0.0, 0.0)),
         ("yellow", None, (1.0, 1.0, 0.0)),
         ("#ff0000", "tuple", (1, 0, 0)),
         ("#0000FF", "tuple", (0, 0, 1)),
         ("white", "hash", "#ffffff"),
         ("black", "hash", "#000000"),
         ("#FFFFFF", "hash", "#FFFFFF")])
    def test_lookup_color_to_tuple(self, input_color, format, expected):
        if format is not None:
            kwargs = {'format': format}
            if format == 'tuple':
                use_allclose = True
            else:
                use_allclose = False
        else:
            kwargs = {}
            use_allclose = True

        actual = ginga.colors.lookup_color(input_color, **kwargs)
        if use_allclose:
            assert_allclose(actual, expected)
        else:
            assert actual == expected

    @pytest.mark.parametrize(
        ('args', 'errtype'),
        [(("unknown_color", ), KeyError),
         (("unknown_key", ), KeyError),
         (("White", ), KeyError),
         (("#af8dc3", "name"), ValueError),
         (("white", "unknown_format"), ValueError)])
    def test_lookup_color_unknown(self, args, errtype):
        with pytest.raises(errtype):
            ginga.colors.lookup_color(*args)

    # Tests for the resolve_color() function

    @pytest.mark.parametrize(
        ('color_input', 'expected'),
        [('red', (1.0, 0.0, 0.0)),
         ('#FF0000', (1.0, 0.0, 0.0)),
         ('#00ff00', (0.0, 1.0, 0.0)),
         ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0))])
    def test_resolve_color(self, color_input, expected):
        assert_allclose(ginga.colors.resolve_color(color_input), expected)

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
        assert_allclose(expected, actual)

        ginga.colors.remove_color("test_color_white")
        with pytest.raises(KeyError):
            ginga.colors.remove_color("test_color_white")

    @pytest.mark.parametrize(
        ('colorname', 'colorval', 'errtype'),
        [("white", "string_wrong_format", TypeError),
         ("test_color", (-1.0, 0.0, 0.0), ValueError),
         ("test_color", (0.0, 0.0), ValueError)])
    def test_add_color_wrong(self, colorname, colorval, errtype):
        with pytest.raises(errtype):
            ginga.colors.add_color(colorname, colorval)

    def test_remove_color_unknown(self):
        with pytest.raises(KeyError):
            ginga.colors.remove_color("unknown_color")

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
        assert_allclose(expected, actual)

# END
