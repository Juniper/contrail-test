import logging
import subprocess
import os
import time


class CustomFileHandler(logging.FileHandler):
# def __init__( self, path='', fileName='test_details.log', mode='a',
# build_id='0000'):

    def __init__(self, fileName='test_details.log', mode='a', build_id='0000'):
#        ts=time.strftime("%Y%m%d%H%M%S")
#        path = path+"/log_%s_%s" %( build_id, ts )
#        super(CustomFileHandler,self).__init__(path+"/"+fileName,mode)
        if 'SCRIPT_TS' in os.environ:
            ts = os.environ.get('SCRIPT_TS')
        else:
            ts = ''
        if 'BUILD_ID' in os.environ:
            build_id = os.environ.get('BUILD_ID')
        path = os.environ.get('HOME') + '/logs/' + build_id + '_' + ts
        try:
            os.mkdir(path)
        except OSError:
            subprocess.call('mkdir -p %s' % (path), shell=True)
        fileName = path + '/' + fileName
        print "\nLog file : %s \n" % (os.path.realpath(fileName))
#        super(CustomFileHandler,self).__init__(fileName,mode)
        logging.FileHandler.__init__(self, fileName, mode)
# end customFileHandler
