import functools
import os
import time
from testtools import content, content_type

import fixtures
import testresources
import testtools
from contrail_test_init import ContrailTestInit
from common import log 

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


class BaseTestCase(testtools.TestCase,
                   testtools.testcase.WithAttributes,
                   testresources.ResourcedTestCase):

    setUpClassCalled = False

#    inputs.setUp()

#    def __init__(self):
#        
#        if 'PARAMS_FILE' in os.environ :
#            self.ini_file= os.environ.get('PARAMS_FILE')
#        else:
#            self.ini_file= 'params.ini'	
#        self.inputs=self.useFixture(ContrailTestInit(self.ini_file))


    @classmethod
    def setUpClass(cls):
        if hasattr(super(BaseTestCase, cls), 'setUpClass'):
            super(BaseTestCase, cls).setUpClass()
        cls.setUpClassCalled = True
        
        if 'PARAMS_FILE' in os.environ :
            cls.ini_file= os.environ.get('PARAMS_FILE')
        else:
            cls.ini_file= 'params.ini'	
        cls.Logger = log.ContrailLogger(cls.__name__)
        cls.Logger.setUp()
        cls.logger = cls.Logger.logger

        cls.inputs = ContrailTestInit(cls.ini_file,logger = cls.logger)
        cls.inputs.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.Logger.cleanUp()
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
#        if (os.environ.get('OS_LOG_CAPTURE') != 'False' and
#            os.environ.get('OS_LOG_CAPTURE') != '0'):
#            log_format = '%(asctime)-15s %(message)s'
#            self.useFixture(fixtures.LoggerFixture(nuke_handlers=False,
#                                                   format=log_format))
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

