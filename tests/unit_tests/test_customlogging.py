# -*- coding: utf-8 -*-
import logging
import os
import sys
from io import StringIO

import pytest

from jobtech.common.customlogging import JobtechLogFormatter


def configure_logging():
    logging.basicConfig()
    # Remove basicConfig-handlers and replace with custom formatter.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    stream_handler = logging.StreamHandler()

    f = create_log_formatter()
    stream_handler.setFormatter(f)
    root = logging.getLogger()
    root.addHandler(stream_handler)

    root.setLevel(logging.DEBUG)


def create_log_formatter():
    if os.getenv('FLASK_ENV', '') == 'development':
        is_develop_mode = True
    else:
        is_develop_mode = False
    f = JobtechLogFormatter('%(asctime)s|%(levelname)s|%(name)s|MESSAGE: %(message)s', '%Y-%m-%d %H:%M:%S%z',
                            is_develop_mode=is_develop_mode)
    return f


configure_logging()

testlog = logging.getLogger(__name__)
testlog.debug(logging.getLevelName(testlog.getEffectiveLevel()) + ' log level activated')
testlog.info("Starting %s" % __name__)


@pytest.mark.unit
def test_log_level_develop():
    print('============================', sys._getframe().f_code.co_name, '============================ ')
    JobtechLogFormatter.print_test_log_messages(testlog)

    log_level_name = logging.getLevelName(testlog.getEffectiveLevel())

    assert ('DEBUG' == log_level_name)


@pytest.mark.unit
def test_log_newlines_develop():
    print('============================', sys._getframe().f_code.co_name, '============================ ')

    root = logging.getLogger()
    log_stream = StringIO()

    string_io_handler = logging.StreamHandler(stream=log_stream)
    f = JobtechLogFormatter('%(asctime)s|%(levelname)s|%(name)s|MESSAGE: %(message)s', is_develop_mode=True)
    string_io_handler.setFormatter(f)
    root.addHandler(string_io_handler)
    root.handlers[0].setFormatter(f)
    testlog.debug('''hello\nworld''')
    logrow_val = log_stream.getvalue()
    assert ('\r' not in logrow_val)


@pytest.mark.unit
def test_log_newlines_production():
    print('============================', sys._getframe().f_code.co_name, '============================ ')

    root = logging.getLogger()
    log_stream = StringIO()
    string_io_handler = logging.StreamHandler(stream=log_stream)
    f = JobtechLogFormatter('%(asctime)s|%(levelname)s|%(name)s|MESSAGE: %(message)s', is_develop_mode=False)
    string_io_handler.setFormatter(f)
    root.addHandler(string_io_handler)
    root.handlers[0].setFormatter(f)
    testlog.debug('''hello\nworld\r''')
    logrow_val = log_stream.getvalue()
    assert ('hello\rworld\n' in logrow_val)


@pytest.mark.unit
def test_log_newlines_correct_lastchar():
    print('============================', sys._getframe().f_code.co_name, '============================ ')

    root = logging.getLogger()
    log_stream = StringIO()
    string_io_handler = logging.StreamHandler(stream=log_stream)
    f = JobtechLogFormatter('%(asctime)s|%(levelname)s|%(name)s|MESSAGE: %(message)s', is_develop_mode=False)
    string_io_handler.setFormatter(f)
    root.addHandler(string_io_handler)
    root.handlers[0].setFormatter(f)
    testlog.debug('''hello\nworld''')
    logrow_val = log_stream.getvalue()

    assert (logrow_val.endswith('\n'))


if __name__ == '__main__':
    pytest.main([os.path.realpath(__file__), '-svv', '-ra', '-m unit'])
