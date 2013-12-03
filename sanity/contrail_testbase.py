import sys
import time
import datetime
import unittest
import logging
import os
from fabric.api import env
from fabric.api import run, put
from fabric.context_managers import settings
from netaddr import *
import ConfigParser
import HTML
from util import *
from email.mime.text import MIMEText
import smtplib
import getpass

class ContrailTestBase(unittest.TestCase):
    def __init__(self, iniFile , build_id, single_node):
        self.build_id= build_id
        self.single_node= single_node
        self.ini_file = iniFile
        config = ConfigParser.ConfigParser()
        config.read(iniFile)
        self.provFile=config.get('Basic','provFile')
#        self.masterHost=config.get('Basic', 'masterHost')
#        self.hostname= config.get('Basic', 'hostname')
        self.logScenario=config.get('Basic','logScenario')
        self.username=config.get('Basic','username')
        self.password=config.get('Basic','password')
        self.sumLogScenario='Summary-' +  self.logScenario
        self.caseList=config.get('Basic','caseList')
        self.key=config.get('Basic', 'key')
        
        #WebServer
#        self.webServer, self.webServerPath=config.get('Basic','webServer').split(':')
        self.webServer= config.get('WebServer','host')
        self.webServerPath= config.get('WebServer', 'path')
        self.webServerUser= config.get('WebServer', 'username')
        self.webServerPassword= config.get('WebServer', 'password')
        self.webRoot= config.get('WebServer', 'webRoot')
        
        #SMTP
        self.smtpServer= config.get('Mail','server')
        self.smtpPort= config.get('Mail','port')
        self.mailSender=config.get('Mail','mailSender')
        self.mailTo=config.get('Mail','mailTo')
        
        self.cases= self._parseCaseList(self.caseList)
        if 'EMAIL_PWD' in os.environ :
            self.p=os.environ.get('EMAIL_PWD')
        else:
            self.p=getpass.getpass(prompt='Enter password for  '+self.mailSender+' : ')

        ts=time.strftime(".%Y%m%d%H%M%S")
        self.runStartTime=datetime.datetime.now()
        self.runStartTimeStr=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        #Detailed log file
#        logging.config.fileConfig(provFile)
#        self.logger=logging.getLogger('Sanity')
#        self.sumLogger=logging.getLogger('Sanity-Summary')

        # Initialize Detailed log file
        self.logPath= config.get('Basic', 'logPath')
        if not os.path.isdir(self.logPath):
            os.system('mkdir -p '+self.logPath)
#        self.logFile= self.logPath +'/sanity.log'+ ts
        self.logFile= '%s/sanity.log.%s%s' %(self.logPath, self.build_id, ts)
        self.logger=logging.getLogger(self.logScenario)
        handler=logging.FileHandler(self.logFile)
        formatter = logging.Formatter('%(asctime)s [ %(levelname)5s ] %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        handler1= logging.FileHandler('/dev/stdout/')
        handler1.setFormatter(formatter)
        self.logger.addHandler(handler1)
        #Initialize Summary log file
        self.sumLogFile= self.logPath+ '/sanity.log.'+self.build_id+'.summary'+ ts
        self.sumLogger=logging.getLogger(self.sumLogScenario)
        sFormatter = logging.Formatter('%(message)s')
        sHandler=logging.FileHandler(self.sumLogFile)
        sHandler.setFormatter(sFormatter)
        self.sumLogger.addHandler(sHandler)
        self.sumLogger.setLevel(logging.DEBUG)

        #HTML Report file
        self.htmlFile=self.logPath+'/sanity.log.'+ self.build_id+ ts + '.html'
        self.htmlHandle=open(self.htmlFile, 'w')

        self.totalTests=0
        self.passedTests=0
        self.failedTests=0
        self.resultTable=[]
        self.addLogHeaders()
    # end __init__
   
    def addLogHeaders(self):
        initial='\nSTARTING TESTS\n\
                             \nLOG FILE : '+self.logFile+ '\
                             \nBUILD ID : '+self.build_id+ '\
                             \nSTART TIME : '+str(self.runStartTimeStr)
        self.logger.info(initial)
        self.sumLogger.info(initial)
        self.createHTMLFile()
         
    def createHTMLFile(self):
        header='<html> <head> <title> Sanity Report [Build %s] - %s- </title> </head> <body>' %(self.build_id, self.runStartTimeStr)
        header+='<h1>  Sanity Report [Build %s] </h2> <br>Start Time : %s <br> <p>' %(self.build_id, self.runStartTimeStr)
        self._result_colors = {
            'PASSED':      'lime',
            'FAILED':      'red',
        }
        self.htmlHandle.write(header)
    #end createHTMLFile
   
    @retry(delay=10) 
    def sendMail(self, file):
        textfile=file
        fp = open(textfile, 'rb')
        msg = MIMEText(fp.read(),'html')
        fp.close()

        msg['Subject'] = 'Sanity Report [Build %s] %s' %(self.build_id, self.runStartTimeStr)
        msg['From'] = self.mailSender
        msg['To'] = self.mailTo

#        s = smtplib.SMTP('172.24.192.33','587')
        s= None
        try:
            s = smtplib.SMTP(self.smtpServer, self.smtpPort)
        except Exception,e:
            print "Unable to connect to Mail Server"
            return False
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(self.mailSender, self.p)
        s.sendmail(self.mailSender, [self.mailTo], msg.as_string())
        s.quit()
        return True
    #end sendMail
    
    def uploadResults(self):
        self.logger.info('Saving logs to '+self.webServer)
        try:
            with settings(host_string=self.webServer, user=self.webServerUser, password= self.webServerPassword,
                         warn_only=True, abort_on_prompts=True ):
                output=put(self.logFile, self.webServerPath)
                self.logger.info(output)
                output=put(self.sumLogFile, self.webServerPath)
                self.logger.info(output)
                output=put(self.htmlFile, self.webServerPath)
                self.logger.info(output)
        except Exception:
            self.logger.exception('Error occured while uploading the logs to the Web Server ')
            return 0
        return 1
    #end uploadResults  
    
    def writeHTMLResults(self ):
        result_colors = {
            1 :      'lime',
            0 :      'red',
        }
        result_str = {
            1 : 'PASSED',
            0 : 'FAILED'
        }
        t = HTML.Table(header_row=['ID','Description', 'Result'])
        table=self.resultTable
        for index in table:
            # create the colored cell:
            color=''
            color = str(result_colors[index[2]])
            colored_result=HTML.TableCell(result_str[index[2]], bgcolor=color)
            t.rows.append([index[0], index[1], colored_result])
        #end for
        htmlcode=str(t)
        self.htmlHandle.write(htmlcode)
        self.htmlHandle.write('<p>Total Tests  : ' + str(self.totalTests)+'<br>')
        self.htmlHandle.write('Passed Tests  : ' + str(self.passedTests)+'<br>')
        self.htmlHandle.write('Failed Tests  : ' + str(self.failedTests)+'<br>')
        self.htmlHandle.write('<p>Run Duration : '+ str(self.runDuration)+'<br>')
        logFileName=self.logFile.split('/')[-1]
        link='http://'+self.webServer+'/'+ self.webRoot+'/logs/'+logFileName
        logLink=HTML.link(link,link)
        self.htmlHandle.write('Log File      : '+ logLink+'<br>')
        self.htmlHandle.write('<p></body>')
        self.htmlHandle.close()
    #end writeHTMLResults 
    
    def logPass(self,text):
        self.logger.info(' *** PASS *** '+text+'\n\n') 
    
    def logFail(self,text):
        self.logger.error(' *** FAIL *** '+ text+ '\n\n') 
    
    def indicateStartTest(self, testId, description):
        self.logger.info('-' * 80)
        self.logger.info('Test ID '+str(testId)+' : '+description.upper())
        self.logger.info('')
    
    def indicateEndTest(self, testId, description, result):
        if result == 1 : 
            resultStr='PASSED'
        else:   
            resultStr='FAILED'
        self.logger.info('Test ID '+str(testId)+ ' : [' + resultStr + '] '+ description.upper() )
        self.logger.info('-' * 80)
        self.logger.info('')
        self.sumLogger.info(' %03s. %s : [ %6s ]', testId, "{:<60}".format(description.upper()), resultStr)
    #end indicateEndTest
    
    def runTest(self, function, test_id, description, **kwargs):
        if self.caseList == 'ALL' or test_id in self.cases :
            self.indicateStartTest(test_id, description)
            self.totalTests = self.totalTests + 1
            result=function(**kwargs)
            if result:
                self.passedTests = self.passedTests + 1
            else:
                self.failedTests = self.failedTests + 1
            self.indicateEndTest(test_id, description, result)
            self.resultTable.append([test_id, description, result])
        #end if
    #end runTest
 
    def endTests(self):
        str1='*' * 30 
        content= '\n'+'\
                 '+str1 + 'FINAL RESULTS ' + str1 +'\n\
                 \t\t\tTOTAL TESTS   : ' + repr(self.totalTests) + '\n\
                 \t\t\tPASSED TESTS  : ' + repr(self.passedTests) + '\n\
                 \t\t\tFAILED TESTS  : ' + repr(self.failedTests) + '\n\
                 '+ str1 + str1 + '\n'
      
        self.logger.info(content)
        self.sumLogger.info(content)
        endTime=datetime.datetime.now()
        diff=endTime - self.runStartTime
        self.sumLogger.info('RUN DURATION  : '+ str(diff))
        self.runDuration=str(diff)
        self.writeHTMLResults()
        self.uploadResults()
        self.sendMail(self.htmlFile)
        # Just print log file location to stdout
        print ""
        print "Log File     : %s" %(self.logFile)
        print "Summary File : %s" %(self.sumLogFile) 
        print ""
    #end __del__
       
    def sleep(self,duration):
        self.logger.info('Sleeping for '+repr(duration)+' secs')
        time.sleep(duration)
    
    def _parseCaseList(self, caseListStr):
        if caseListStr == 'ALL':
            return ''
        return sum(((list(range(*[int(j) + k for k,j in enumerate(i.split('-'))]))
            if '-' in i else [int(i)]) for i in caseListStr.split(',')), [])
    #end parseCaseList
     
#end class ContrailTestBase
