#!/usr/bin/python2.7

import syslog
import random
import time
import sys


def send_10_log_messages_with_delay():
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_MAIL)
    for ind in range(10):
        msg = str(ind + 1) + '. Test Syslog Messages being sent.'
        syslog.syslog(syslog.LOG_EMERG, msg)
        time.sleep(1)
    syslog.closelog()
# end send_10_log_messages_with_delay


def send_10_log_messages():
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_MAIL)
    for ind in range(10):
        msg = str(ind + 1) + '. Test Syslog Messages being sent without delay.'
        syslog.syslog(syslog.LOG_EMERG, msg)
    syslog.closelog()
# end send_10_log_messages


def send_messages_grater_than_1024_bytes():
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_MAIL)
    with open("message.txt", "r") as myfile:
        msg = myfile.readlines()[0]
        myfile.close()

    for ind in range(100):
        syslog.syslog(
            syslog.LOG_EMERG, (msg[:5] + str(ind) + 'mymark' + msg[6:]))
        time.sleep(1)
    syslog.closelog()
# end send_messages_grater_than_1024_bytes


def send_messages_of_all_facility_and_severity():
    dict_of_facility = {
        'LOG_KERN': 0,
        'LOG_USER': 1,
        'LOG_MAIL': 2,
        'LOG_DAEMON': 3,
        'LOG_AUTH': 4,
        'LOG_NEWS': 7,
        'LOG_UUCP': 8,
        'LOG_LOCAL0': 16,
        'LOG_CRON': 15,
        'LOG_SYSLOG': 5,
        'LOG_LOCAL1': 17}
    list_of_severity = ['LOG_EMERG', 'LOG_ALERT', 'LOG_CRIT', 'LOG_ERR',
                        'LOG_WARNING', 'LOG_NOTICE', 'LOG_INFO', 'LOG_DEBUG']

    for each_facility in dict_of_facility:
        log_facility = dict_of_facility[each_facility]
        syslog.openlog(logoption=syslog.LOG_PID, facility=log_facility)
        for each_severity in list_of_severity:
            log_severity = list_of_severity.index(each_severity)
            msg = 'Test Message from ' + each_facility + \
                ' with severity ' + each_severity + '.'
            syslog.syslog(log_severity, msg)
        syslog.closelog()
        time.sleep(1)
# end send_messages_of_all_facility_and_severity

def send_test_log_message():
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_KERN)
    for ind in range(5):
        msg = str(ind + 1) + '. Test Syslog Messages from different nodes.'
        syslog.syslog(syslog.LOG_EMERG, msg)
    time.sleep(1)
    syslog.closelog()
# end send_test_log_message

help_string = '\nusage:\n\n./mylogging.py <function-name>\n\nwhere function names are:\
              \n1. send_10_log_messages\n2. send_10_log_messages_with_delay\
              \n3. send_messages_grater_than_1024_bytes\n4. send_messages_of_all_facility_and_severity\
              \n5. send_test_log_message\n\n'

FuncCallDict = {
    'send_10_log_messages': send_10_log_messages,
    'send_test_log_message': send_test_log_message,
    'send_10_log_messages_with_delay': send_10_log_messages_with_delay,
    'send_messages_grater_than_1024_bytes': send_messages_grater_than_1024_bytes,
    'send_messages_of_all_facility_and_severity': send_messages_of_all_facility_and_severity}

NumberOfArgs = len(sys.argv)
if NumberOfArgs != 2:
    print help_string
    sys.exit(2)

FunctionName = sys.argv[1]
FuncCallDict[FunctionName]()
