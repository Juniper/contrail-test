""" Module to check and collect information about errors and exceptions during the test."""
import re

from fabric.api import run, cd, get
from fabric.context_managers import settings, hide

logfile = "/var/log/cloudstack/management/management-server.log"
tmpfile = "/tmp/.logfile.tmp"

def get_errors(nodes, user, password):
    """Get the Cloudstack management server error logs from the ACS controller.
    """
    errors = {}

    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' %(user, node), password=password,
                          warn_only=False, debug=True, abort_on_prompts= False ):
                try:
                    get(logfile, tmpfile)
                except Exception as e:
                    #self.log.error("Error during get logfile %s"%e.strerror)
                    print "Error during get logfile ", e
        with open(tmpfile) as syslogFile:
            dump = syslogFile.read()
            m = re.findall(r"^([\d\-\:,\s]+ERROR.*)", dump, re.M)
            if m:
                errors.update({node : m})
    return errors

def get_exceptions(nodes, user, password):
    """Get the exceptions from the Cloudstack management server logs of the ACS controller.
    """
    exceptions = {}

    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' %(user, node), password=password,
                          warn_only=False, debug=True, abort_on_prompts= False ):
                try:
                    get(logfile, tmpfile)
                except Exception as e:
                    print "Error during get logfile ", e
        with open(tmpfile) as syslogFile:
            dump = syslogFile.read()
            m = re.findall(r"^(.*Exception:.*)", dump, re.M)
            if m:
                exceptions.update({node : m})
    return exceptions

def zeroize_logfile(nodes, user, password):
    """Trim the logfile(s)
    """
    #open(tmpfile, 'w').close()
    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' %(user, node), password=password,
                          warn_only=False, debug=True, abort_on_prompts= False ):
                try:
                    run(">| %s"%logfile)
                except Exception as e:
                    print "Error during put empty file ",e

def copy_logfile(nodes, user, password, localfile):
    """copy the logfile(s) to the local log dir
    """
    for node in nodes:
        with hide('everything'):
            with settings(host_string='%s@%s' %(user, node), password=password,
                          warn_only=False, debug=True, abort_on_prompts= False ):
                try:
                    get(logfile, localfile)
                except Exception as e:
                    print "Error during get logfile on host host_string", e

