import ConfigParser
import logging
import logging.config
import logging.handlers
import os
import sys
import subprocess
import time
import fixtures
import datetime

cwd = os.path.join(os.path.dirname(__file__), os.pardir)
LOG_KEY = 'default'
TS = time.time()
ST = datetime.datetime.fromtimestamp(TS).strftime('%Y-%m-%d_%H:%M:%S')

if not '_loggers' in locals():
    _loggers = {}

class NullHandler(logging.Handler):
    """
    For backward-compatibility with Python 2.6, a local class definition
    is used instead of logging.NullHandler
    """

    def handle(self, record):
        pass

    def emit(self, record):
        pass

    def createLock(self):
        self.lock = None

def getLogger(name='unknown',**kwargs):
    if name not in _loggers:
        _loggers[name] = ContrailLogger(name=name, **kwargs)
        _loggers[name].setUp()
    return _loggers[name].logger

class ContrailLogger:
    def __init__(self, name, log_to_console=True, max_message_size=None):
        self.name = name
        self.logger = logging.getLogger(name or LOG_KEY)
        self.logger.disabled = False
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.log_file = name
        self.log_to_console = log_to_console
        self.console_h = None
        if not max_message_size:
            max_message_size = ''
        self.log_format = logging.Formatter('%(asctime)s - %(levelname)s'
                              ' - %(message)' + '%ss' %(str(max_message_size)))

    def setUp(self):
        self.fileHandler = CustomFileHandler(fileName = self.log_file)
        self.fileHandler.setFormatter(self.log_format)
        self.fileHandler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.fileHandler)

        if self.log_to_console:
            self.console_h= logging.StreamHandler()
            self.console_h.setLevel(logging.INFO)
            self.console_h.setFormatter(self.log_format)
            self.logger.addHandler(self.console_h)
        self.logger.addHandler(NullHandler())

    def cleanUp(self):
        pass
        if self.console_h:
            self.logger.removeHandler(self.console_h)

    def handlers(self):
        return self.logger.handlers

class CustomFileHandler(logging.FileHandler):
    def __init__( self, fileName='test_details.log', mode='a', build_id='0000'):
        if 'SCRIPT_TS' in os.environ:
            ts= os.environ.get('SCRIPT_TS')
        else:
            ts=''
        if 'BUILD_ID' in os.environ :
            build_id= os.environ.get('BUILD_ID')
        #path=os.environ.get('%s',%cwd)+'/logs/' 
        path=('%s'+'/logs/')%cwd 
        try:
            os.mkdir( path )
        except OSError:
            subprocess.call('mkdir -p %s' %(path), shell=True)
        fileName= path + '/' + fileName.lower() +'.log'
        logging.FileHandler.__init__(self,fileName,mode)

def dolog(logger,message = ''):

    logger.debug("Debug %s"%message)
    logger.info("Info %s"%message)
    logger.warning("Warning %s"%message)
    logger.error("Error %s"%message)
    logger.critical("Critical %s"%message)

def main():

    logger = Contrail_Logger('Dummy_file')
    logger.setUp()
    dolog(logger.logger,'message1')
    logger.cleanUp()
    
    logger = Contrail_Logger('Dummy_file_1')
    logger.setUp()
    dolog(logger.logger,'message2')
    logger.cleanUp()

if __name__ == "__main__":
    main()
