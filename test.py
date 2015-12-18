import functools
import os
import time
from testtools import content, content_type

import fixtures
import testresources
import testtools
from common.contrail_test_init import ContrailTestInit
from common import log_orig as logging
#from common import config
import logging as std_logging
from tcutils.util import get_random_name

def attr(*args, **kwargs):
    """A decorator which applies the  testtools attr decorator

    This decorator applies the testtools.testcase.attr if it is in the list of
    attributes to testtools we want to apply.
    """

    def decorator(f):
        if 'type' in kwargs and isinstance(kwargs['type'], str):
            f = testtools.testcase.attr(kwargs['type'])(f)
        elif 'type' in kwargs and isinstance(kwargs['type'], list):
            for attr in kwargs['type']:
                f = testtools.testcase.attr(attr)(f)
        return f

    return decorator

#LOG = logging.getLogger(__name__)
std_logging.getLogger('urllib3.connectionpool').setLevel(std_logging.WARN)
std_logging.getLogger('paramiko.transport').setLevel(std_logging.WARN)
std_logging.getLogger('keystoneclient.session').setLevel(std_logging.WARN)
std_logging.getLogger('keystoneclient.httpclient').setLevel(std_logging.WARN)
std_logging.getLogger('neutronclient.client').setLevel(std_logging.WARN)
#
#CONF = config.CONF

class TagsHack(object):
    def id(self):
        orig = super(TagsHack, self).id()
        tags = os.getenv('TAGS', '')
        if not tags:
            return orig
        else:
            fn = self._get_test_method()
            attributes = getattr(fn, '__testtools_attrs', None)
            tags = tags.split(" ")
            if attributes:
                for tag in tags:
                    if tag in attributes:
                        return orig
            # A hack to please testtools to get uniq testcase names
            return get_random_name()

class BaseTestCase(TagsHack,
                   testtools.testcase.WithAttributes,
                   testtools.TestCase,
                   testresources.ResourcedTestCase):

    setUpClassCalled = False

    @classmethod
    def setUpClass(cls):
        if hasattr(super(BaseTestCase, cls), 'setUpClass'):
            super(BaseTestCase, cls).setUpClass()
        cls.setUpClassCalled = True
        
        if 'TEST_CONFIG_FILE' in os.environ :
            cls.ini_file= os.environ.get('TEST_CONFIG_FILE')
        else:
            cls.ini_file= 'sanity_params.ini'	
        cls.Logger = logging.ContrailLogger(cls.__name__)
        cls.Logger.setUp()
        cls.logger = cls.Logger.logger
        cls.inputs = ContrailTestInit(cls.ini_file,logger = cls.logger)

    @classmethod
    def tearDownClass(cls):
        #cls.logger.cleanUp()
        if hasattr(super(BaseTestCase, cls), 'tearDownClass'):
            super(BaseTestCase, cls).tearDownClass()

    def setUp(self):
        super(BaseTestCase, self).setUp()
        if not self.setUpClassCalled:
            raise RuntimeError("setUpClass did not call the super's"
                               " setUpClass in the "
                               + self.__class__.__name__)

        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 0)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        if (os.environ.get('OS_STDOUT_CAPTURE') == 'True' or
		os.environ.get('OS_STDOUT_CAPTURE') == '1'):
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if (os.environ.get('OS_STDERR_CAPTURE') == 'True' or
                os.environ.get('OS_STDERR_CAPTURE') == '1'):
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))
        if (os.environ.get('OS_LOG_CAPTURE') != 'False' and
            os.environ.get('OS_LOG_CAPTURE') != '0'):
            log_format = '%(asctime)-15s %(message)s'
            self.useFixture(fixtures.LoggerFixture(nuke_handlers=False,
                                                   format=log_format))
#        import pdb;pdb.set_trace()
#        logger = self.useFixture(log.Contrail_Logger(cls.__name__))
#

    def cleanUp(self):
        super(BaseTestCase, self).cleanUp()

    def addDetail(self, logfile, text):
        if type(text) is str:
            super(BaseTestCase, self).addDetail(logfile, 
                  content.text_content(text))
        else:
            super(BaseTestCase, self).addDetail(logfile, text)

    def is_test_applicable(self):
        return (True, None)


def call_until_true(func, duration, sleep_for):
    """
    Call the given function until it returns True (and return True) or
    until the specified duration (in seconds) elapses (and return
    False).

    :param func: A zero argument callable that returns True on success.
    :param duration: The number of seconds for which to attempt a
        successful call of the function.
    :param sleep_for: The number of seconds to sleep after an unsuccessful
                      invocation of the function.
    """
    now = time.time()
    timeout = now + duration
    while now < timeout:
        if func():
            return True
        LOG.debug("Sleeping for %d seconds", sleep_for)
        time.sleep(sleep_for)
        now = time.time()
    return False
