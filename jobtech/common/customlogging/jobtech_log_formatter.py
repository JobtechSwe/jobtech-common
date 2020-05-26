import logging
import json
import os


def configure_logging(local_modules=[]):
    logging.basicConfig(level=logging.DEBUG)
    # Remove basicConfig-handlers and replace with custom formatter.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    stream_handler = logging.StreamHandler()

    f = create_log_formatter()
    stream_handler.setFormatter(f)
    root = logging.getLogger()
    # root.setLevel(logging.INFO)
    root.addHandler(stream_handler)

    set_custom_log_level(local_modules)


def create_log_formatter():
    if os.getenv('FLASK_ENV', '') == 'development':
        is_develop_mode = True
    else:
        is_develop_mode = False
    f = JobtechLogFormatter('%(asctime)s|%(levelname)s|%(name)s|MESSAGE: %(message)s',
                            '%Y-%m-%d %H:%M:%S%z', is_develop_mode=is_develop_mode)
    return f


def set_custom_log_level(local_modules):
    # Set log level debug for module specific events
    # and level warning for all third party dependencies
    master_module = str(__name__).split('.')[0]
    local_modules.append(master_module)
    local_module = False
    for key in logging.Logger.manager.loggerDict:
        for lm in local_modules:
            if key.startswith(lm):
                local_module = True
        if local_module:
            llevel = os.getenv('LOGLEVEL', '')
            if llevel == 'debug':
                print("Setting loglevel DEBUG for %s" % key)
                logging.getLogger(key).setLevel(logging.DEBUG)
            elif llevel == 'warning':
                print("Setting loglevel WARNING for %s" % key)
                logging.getLogger(key).setLevel(logging.WARNING)
            elif llevel == 'error':
                print("Setting loglevel ERROR for %s" % key)
                logging.getLogger(key).setLevel(logging.WARNING)
            else:  # Default to loglevel INFO
                print("Setting loglevel INFO for %s" % key)
                logging.getLogger(key).setLevel(logging.INFO)
        else:
            logging.getLogger(key).setLevel(logging.WARNING)
        local_module = False


class JobtechLogFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', is_develop_mode=False):
        super().__init__(fmt, datefmt, style)

        self.is_develop_mode = is_develop_mode

        if is_develop_mode is True:
            self.linesep = os.linesep
            print('JobtechLogFormatter configured to development mode.')
        else:
            self.linesep = '\r'
            print('JobtechLogFormatter is configured with newline separator \\r')

    @staticmethod
    def lastreplace(str_input, old, new):
        li = str_input.rsplit(old, maxsplit=1)
        return new.join(li)

    def format(self, record):
        is_json_str = False
        json_obj = None
        # print(type(record.msg))
        if type(record.msg) == str and '{' in record.msg:
            try:
                json_obj = json.loads(record.msg)
                is_json_str = True
            except ValueError:
                # print('Got ValueError when trying json.loads')
                pass

        if is_json_str and json_obj is not None:
            message = json.dumps(json_obj)
            record.msg = message

        result = super(JobtechLogFormatter, self).format(record)
        # Replace all occurances of '|n' to wanted lineseparator
        # since openshift makes newline with '\r' and new logrow
        # with '\n'
        result = result.replace('\n', self.linesep)
        # Replace last occurrence of lineseparator to '\n’ to
        # create separate log-row in openshift.
        if result.endswith(self.linesep):
            result = self.lastreplace(result, self.linesep, '\n')

        if not self.is_develop_mode and not result.endswith('\n'):
            result = result + '\n'

        return result

    def formatException(self, exc_info):
        result = super(JobtechLogFormatter, self).formatException(exc_info)
        return result.replace('\n', self.linesep)

    def formatMessage(self, record):
        result = super(JobtechLogFormatter, self).formatMessage(record)
        return result.replace('\n', self.linesep)

    @classmethod
    def print_test_log_messages(cls, log):
        log.info('Testing log levels - BEGIN')

        test_dict = {
            "prop1": "dict_val1",
            "prop2": "dict_val2",
            "inner": {
                "innerobjprop": "innerobjval"
            }
        }
        log.debug(test_dict)

        test_json = '''{
            "jsontestprop1": "jsontestval1",
            "jsontestprop2": "jsontestval2"

        }'''

        log.debug(test_json)

        test_non_json = '''function test{
                                alert('just testing logging...');
                            }'''
        log.debug(test_non_json)

        try:
            json.loads('not a json-string')
        except ValueError:
            logging.exception('Testmessage for exception')

        test_newline = '''hello
                    world
                    test'''
        log.debug(test_newline)

        log.info('Testing log levels - END')
