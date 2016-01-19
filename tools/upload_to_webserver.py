import sys
from fabric.api import env, run , local
from fabric.operations import get, put
from fabric.context_managers import settings, hide
import os
import ConfigParser
import subprocess
from tcutils.util import read_config_option
import logging

logging.getLogger("paramiko").setLevel(logging.WARNING)

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
    http_proxy = read_config_option(config, 'proxy', 'proxy_url', None)

    if not (web_server and web_server_report_path and web_server_log_path and \
            web_server_username and web_server_password):
       print "Not all webserver details are available. Skipping upload."
       return False
    report_config = ConfigParser.ConfigParser()
    report_config.read(report_config_file)
    ts = report_config.get('Test', 'timestamp')
    log_scenario = report_config.get('Test', 'logScenario')
    build_id = report_config.get('Test', 'build')
    distro_sku = report_config.get('Test','distro_sku')
    branch = get_os_env('BRANCH', 'unknown-branch')

    test_type = get_os_env('TEST_TYPE','daily')
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
                    sanity_report = '%s/%s' % (
                        web_server_report_path, test_type)
                    # report name in format
                    # email_subject_line+time_stamp
                    report_name = '%s %s' % (distro_sku.replace('"',''),
                                            log_scenario)
                    report_file = "%s-%s.html" % (
                        '-'.join(report_name.split(' ')), ts)
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
                    branch = build_id.split('-')[0]
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
                    ci_job_type = os.environ.get('TAGS', None)
                    if 'ci_sanity_WIP' in ci_job_type:
                        web_server_path_ci = web_server_log_path + '/CI_WIP_JOBS/'
                    else:
                        web_server_path_ci = web_server_log_path + '/CI_JOBS/'
                    web_server_path_ci_build = web_server_path_ci + branch + '/'
                    web_server_path = web_server_path_ci_build + build_folder + '/'
                    subprocess.check_output(
                        "sshpass -p %s ssh %s@%s mkdir -p %s" %
                        (web_server_password, web_server_username,
                         web_server, web_server_path_ci),
                        shell=True)
                    subprocess.check_output(
                        "sshpass -p %s ssh %s@%s mkdir -p %s" %
                        (web_server_password, web_server_username,
                         web_server, web_server_path_ci_build),
                        shell=True)
                    subprocess.check_output(
                        "sshpass -p %s ssh %s@%s mkdir -p %s" %
                        (web_server_password, web_server_username,
                         web_server, web_server_path),
                        shell=True)
                    subprocess.check_output(
                        "sshpass -p %s scp -r /root/contrail-test/logs %s %s@%s:%s" %
                        (web_server_password, elem,
                         web_server_username, web_server,
                         web_server_path), shell=True)
                else:
                    run('mkdir -p %s' % (web_server_path))
                    output = put(elem, web_server_path)
                    put('logs', web_server_path)
                    put('result*.xml', web_server_path)
                    put(report_config_file, web_server_path)
                    if jenkins_trigger:
                        #run('cd %s/%s; mkdir -p %s; cd %s; ln -s %s/junit-noframes.html %s'
                        run('cd %s/%s; mkdir -p %s; cd %s; cp %s/%s .'
                            % (sanity_report, branch, build_id, build_id,
                                web_server_path, report_config_file))

    except Exception,e:
        print 'Error occured while uploading the logs to the Web Server ',e
        return False
    return True

# end 

if __name__ == "__main__":
    # accept sanity_params.ini, report_details.ini, result.xml
    upload_to_webserver(sys.argv[1], sys.argv[2], sys.argv[3])
