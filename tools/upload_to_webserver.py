import sys
from fabric.api import env, run , local
from fabric.operations import get, put
from fabric.context_managers import settings, hide
import os
import ConfigParser
import subprocess
from tcutils.util import read_config_option

#monkey patch subprocess.check_output cos its not supported in 2.6
if "check_output" not in dir( subprocess ): # duck punch it in!
    def f(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = f

def get_os_env(var, default=''):
    if var in os.environ:
        return os.environ.get(var)
    else:
        return default
# end get_os_env

def upload_to_webserver(config_file, report_config_file, elem):

    jenkins_trigger = get_os_env('JENKINS_TRIGGERED')
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    web_server = read_config_option(config, 'WebServer', 'host', None)
    web_server_report_path = read_config_option(config, 'WebServer', 
                                                'reportPath', None)
    web_server_log_path = read_config_option(config, 'WebServer',
                                             'logPath', None)
    web_server_username = read_config_option(config, 'WebServer', 'username', 
                                             None)
    web_server_password = read_config_option(config, 'WebServer', 'password',
                                             None)
    log_scenario = read_config_option(config, 'Basic', 'logScenario', 'Sanity')
    http_proxy = read_config_option(config, 'proxy', 'proxy_url', None)

    if not (web_server and web_server_report_path and web_server_log_path and \
            web_server_username and web_server_password):
       print "Not all webserver details are available. Skipping upload."
       return False
    report_config = ConfigParser.ConfigParser()
    report_config.read(report_config_file)
    ts = report_config.get('Test', 'timestamp')
    build_id = report_config.get('Test', 'build')
    branch = build_id.split('-')[0]

    sanity_type = get_os_env('SANITY_TYPE','Daily')
    build_folder = build_id + '_' + ts
    web_server_path = web_server_log_path + '/' + build_folder + '/'

    log = 'logs'
    print "Web server log path %s"%web_server_path

    try:
        with hide('everything'):
            with settings(host_string=web_server,
                          user=web_server_username,
                          password=web_server_password,
                          warn_only=True, abort_on_prompts=False):
                if jenkins_trigger:
                    # define report path
                    if sanity_type == "Daily":
                        sanity_report = '%s/daily' % (
                            web_server_report_path)
                    else:
                        sanity_report = '%s/regression' % (
                            web_server_report_path)
                    # report name in format
                    # email_subject_line+time_stamp
                    report_file = "%s-%s.html" % (
                        '-'.join(log_scenario.split(' ')), ts)
                    # create report path if doesnt exist
                    run('mkdir -p %s' % (sanity_report))
                    # create folder by release name passed from jenkins
                    run('cd %s; mkdir -p %s' %
                        (sanity_report, branch))
                    # create folder by build_number and create soft
                    # link to original report with custom name
                    run('cd %s/%s; mkdir -p %s; cd %s; ln -s %s/junit-noframes.html %s'
                        % (sanity_report, branch, build_id, build_id,
                            web_server_path, report_file))

                if http_proxy:
                    # Assume ssl over http-proxy and use sshpass.
                    subprocess.check_output(
                        "sshpass -p %s ssh %s@%s mkdir -p %s" %
                        (web_server_password, web_server_username,
                         web_server, web_server_path),
                        shell=True)
                    subprocess.check_output(
                        "sshpass -p %s scp %s %s@%s:%s" %
                        (web_server_password, elem,
                         web_server_username, web_server,
                         web_server_path), shell=True)
                else:
                    run('mkdir -p %s' % (web_server_path))
                    output = put(elem, web_server_path)
                    put('logs', web_server_path)
                    put('result.xml', web_server_path)
                    put('result1.xml', web_server_path)

    except Exception,e:
        print 'Error occured while uploading the logs to the Web Server ',e
        return False
    return True

# end 

if __name__ == "__main__":
    # accept sanity_params.ini, report_details.ini, result.xml
    upload_to_webserver(sys.argv[1], sys.argv[2], sys.argv[3])
