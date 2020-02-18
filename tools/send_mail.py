from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from email.mime.text import MIMEText
import smtplib
import subprocess
import configparser
import sys
import os
import yaml
from tcutils.util import read_config_option

def send_mail(config_file, file_to_send, report_details):
    if config_file.endswith('.ini'):
        config = configparser.ConfigParser()
        config.read(config_file)
        smtpServer = read_config_option(config, 'Mail', 'server', None)
        smtpPort = read_config_option(config, 'Mail', 'port', '25')
        mailSender = read_config_option(config, 'Mail', 'mailSender', 'contrailbuild@juniper.net')
        mailTo = read_config_option(config, 'Mail', 'mailTo', None)
    elif config_file.endswith(('.yml', '.yaml')):
        with open(config_file, 'r') as fd:
            config = yaml.load(fd)
        test_configs = config.get('test_configuration') or {}
        mailserver_configs = test_configs.get('mail_server') or {}
        smtpServer = mailserver_configs.get('server')
        smtpPort = mailserver_configs.get('port') or '25'
        mailTo = mailserver_configs.get('to')
        mailSender = mailserver_configs.get('sender') or 'contrailbuild@juniper.net'

    if not (smtpServer and mailSender and mailTo):
        print("Not all mail server details are available. Skipping mail send.")
        return False

    report_config = configparser.ConfigParser()
    report_config.read(report_details)
    distro_sku = report_config.get('Test','Distro_Sku')
    if 'EMAIL_SUBJECT' in os.environ and os.environ['EMAIL_SUBJECT'] != '':
        logScenario = os.environ.get('EMAIL_SUBJECT')
    else:
        logScenario = report_config.get('Test', 'logScenario')

    if not mailTo or not smtpServer:
        print('Mail destination not configured. Skipping')
        return True
    fp = open(file_to_send, 'rb')
    val = fp.read()
    fp.close()
    if sys.version_info[0] == 3:
        val = val.decode()
    msg = MIMEText(val, 'html')

    msg['Subject'] = '[Build %s] ' % (
         distro_sku) + logScenario + ' Report'
    msg['From'] = mailSender
    msg['To'] = mailTo

    s = None
    try:
        s = smtplib.SMTP(smtpServer, smtpPort)
    except Exception as e:
        print("Unable to connect to Mail Server")
        return False
    s.ehlo()
    try:
        s.sendmail(mailSender, mailTo.split(","), msg.as_string())
        s.quit()
    except smtplib.SMTPException as e:
        print('Error while sending mail')
        return False
    return True
# end send_mail

if __name__ == "__main__":
    #send_mail('sanity_params.ini','report/junit-noframes.html') 
    send_mail(sys.argv[1], sys.argv[2], sys.argv[3])
