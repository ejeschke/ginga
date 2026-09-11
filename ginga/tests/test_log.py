#
# test_log.py -- the logging helpers
#
"""NullLogger stands in for a logger when there is not one, so what matters
is that it can be used exactly like one.  The version it replaces could not:
critical() raised on every call, several standard methods were missing, and
arguments and handlers given to it were silently dropped.
"""

import io
import logging

import pytest

from ginga.misc.log import NullLogger, get_logger


def test_it_is_a_real_logger():
    assert isinstance(NullLogger(), logging.Logger)


def test_it_takes_the_constructor_arguments_a_logger_takes():
    logger = NullLogger('myname', logging.DEBUG)

    assert logger.name == 'myname'
    assert logger.level == logging.DEBUG


def test_it_can_be_built_with_nothing_at_all():
    """Which is how every caller builds it."""
    logger = NullLogger()

    assert logger.name
    assert not logger.isEnabledFor(logging.CRITICAL), 'discards by default'


def test_two_of_them_do_not_share_handlers():
    first, second = NullLogger(), NullLogger()

    assert first.name != second.name
    assert len(first.handlers) == 1 and len(second.handlers) == 1


def test_nothing_escapes_to_the_root_logger():
    """It stands in for having no logger, not for a quiet way into somebody
    else's output."""
    assert not NullLogger().propagate


# ------------------------------------------------ what used to be broken --

def test_critical_can_be_called_at_all():
    """It was declared critical(self, *args, msg), so msg was keyword-only
    and every ordinary call raised TypeError."""
    NullLogger().critical('the sky is falling')


@pytest.mark.parametrize('method,args', [
    ('exception', ('x',)),
    ('log', (logging.INFO, 'x')),
    ('isEnabledFor', (logging.DEBUG,)),
    ('setLevel', (logging.DEBUG,)),
    ('warn', ('x',)),
])
def test_the_methods_that_were_missing(method, args):
    """Code written against the standard library got an AttributeError from
    the object that exists to stand in for it."""
    getattr(NullLogger(), method)(*args)


def test_arguments_are_used_rather_than_dropped():
    """info("x %s", 1) used to log the format string."""
    stream = io.StringIO()
    NullLogger(f_out=stream).info('a %s and a %d', 'string', 2)

    assert 'a string and a 2' in stream.getvalue()


def test_exc_info_is_honoured_rather_than_accepted_and_ignored():
    stream = io.StringIO()
    logger = NullLogger(f_out=stream)
    try:
        raise RuntimeError('kaboom')
    except RuntimeError:
        logger.error('it failed', exc_info=True)

    written = stream.getvalue()
    assert 'it failed' in written
    assert 'kaboom' in written, 'the traceback should be there too'
    assert 'RuntimeError' in written


def test_a_handler_added_is_actually_used():
    """addHandler() did nothing, so anything added to one never saw a
    record."""
    records = []

    class Collecting(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = NullLogger(level=logging.DEBUG)
    logger.addHandler(Collecting())
    logger.info('heard')

    assert [r.getMessage() for r in records] == ['heard']


# ------------------------------------------------------------- output --

def test_the_output_format_is_unchanged():
    stream = io.StringIO()
    logger = NullLogger(f_out=stream)
    logger.debug('dee')
    logger.warning('dubya')
    logger.critical('see')

    assert stream.getvalue().splitlines() == ['| D | dee', '| W | dubya',
                                              '| C | see']


def test_given_a_file_it_writes_and_otherwise_it_does_not():
    stream = io.StringIO()
    assert NullLogger(f_out=stream).isEnabledFor(logging.DEBUG)
    assert not NullLogger().isEnabledFor(logging.DEBUG)


def test_get_logger_still_hands_one_back():
    assert isinstance(get_logger(null=True), NullLogger)
