import logging
import logging.config
import logging.handlers
import os
import sys
import subprocess
import time
import fixtures
import datetime

LOG_CONFIG = '/root/contrail-test/scripts/log_conf.ini'
LOG_KEY = 'log01'
TS = time.time()
ST = datetime.datetime.fromtimestamp(TS).strftime('%Y-%m-%d_%H:%M:%S')
LOG_FORMAT = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

class ContrailLogger:
    def __init__(self,log_file):

        logging.config.fileConfig(LOG_CONFIG)
        self.logger = logging.getLogger(LOG_KEY)
        self.log_file = log_file

    def setUp(self):
        self.fileHandler = CustomFileHandler(fileName = self.log_file)
        self.fileHandler.setFormatter(LOG_FORMAT)
        self.memHandler = self.logger.handlers[0]
        self.memHandler.setTarget(self.fileHandler)
#        self.logger.addHandler(self.memHandler)

        self.console_h= logging.StreamHandler()
        self.console_h.setLevel(logging.INFO)
        self.console_h.setFormatter(LOG_FORMAT)
        self.logger.addHandler(self.console_h)
        self.logger.addHandler(logging.NullHandler())

    def cleanUp(self):
        self.memHandler.flush()
        self.memHandler.close()
        self.logger.removeHandler(self.memHandler)
        self.logger.removeHandler(self.console_h)


class CustomFileHandler(logging.FileHandler):
    def __init__( self, fileName='test_details.log', mode='a', build_id='0000'):
        if 'SCRIPT_TS' in os.environ:
            ts= os.environ.get('SCRIPT_TS')
        else:
            ts=''
        if 'BUILD_ID' in os.environ :
            build_id= os.environ.get('BUILD_ID')
        path=os.environ.get('HOME')+'/logs/'+ build_id + '_' + ST 
        try:
            os.mkdir( path )
        except OSError:
            subprocess.call('mkdir -p %s' %(path), shell=True)
        fileName= path + '/' + fileName.lower() +'.log'
        print "\nLog file : %s \n" %(os.path.realpath(fileName))
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
