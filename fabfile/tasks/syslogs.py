from datetime import datetime as dt

from fabfile.config import *
from fabfile.utils.fabos import detect_ostype
from fabric.contrib.files import exists

@roles('all')
@task
def tar_logs_cores():
    sudo("rm -f /var/log/logs_*.tgz")
    sudo("rm -f /var/crashes/*gz")
    sudo("rm -f /var/log/gdb*.log")
    sudo("rm -f /var/log/contrail*.log")
    sudo("rm -rf /var/log/temp_log")
    sudo("rm -rf /var/temp_log")
    a = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
    d = env.host_string
    e=run('hostname')
    sudo ("mkdir -p /var/temp_log; cp -R /var/log/* /var/temp_log")
    sudo ("mv /var/temp_log /var/log/temp_log")
    sudo ("cd /var/log/temp_log/ ; tar czf /var/log/logs_%s_%s.tgz *"%(e, a))
    if not check_file_exists('/usr/bin/gdb'):
        install_pkg(['gdb'])
    if "core" in sudo("ls -lrt /var/crashes"):
        output = sudo("ls -lrt /var/crashes")
        core_list = output.split('\n')
        for corename in core_list:
            if "core" in corename:
                core = corename.split()[8]
                name = core.split('.')[1]
                core_new = core.rstrip('\r')        
                sudo("gdb %s /var/crashes/%s --eval-command bt > /var/log/gdb_%s.log --eval-command quit"%(name, core_new, core_new))
        sudo ("mkdir -p /var/crashes/saved")
        sudo ("cp /var/crashes/core* /var/crashes/saved/")
        sudo ("gzip /var/crashes/core*")
        sudo ("cd /var/crashes; for i in core*.gz; do mv -f $i %s_$i; done" %(e) )
    sudo("contrail-version > /var/log/contrail_version_%s_%s.log"%(e,a))

#end tar_logs_cores

def check_file_exists(filepath):
    if exists(filepath):
        return True
    return False

def install_pkg(pkgs):
    ostype = detect_ostype()
    for pkg in pkgs:
        with settings(warn_only = True):
            if ostype in [ 'fedora','centos' ]:
                run("yum -y install %s" % (pkg))
            elif ostype in ['Ubuntu']:
                run("DEBIAN_FRONTEND=noninteractive apt-get -y --force-yes install %s" %(pkg))


@roles('collector')
@task
def get_cassandra_logs():
    sudo("rm -f /var/log/cassandra_log_*")
    a = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
    d = env.host_string
    e=run('hostname')
    output = sudo("cat /proc/uptime") 
    uptime_seconds = float(output.split()[0]) 
    uptime_min=uptime_seconds/60
    uptime_min=int(uptime_min) 
    uptime_min=str(uptime_min) + 'm'
    print "Node %s is up for %s. Collecting Cassandra logs for %s" %(e,uptime_min,uptime_min)    
    cmd = "/opt/contrail/utils/contrail-logs --last %s --all" %(uptime_min)
    sudo("%s >> /var/log/cassandra_log_%s_%s.log" %(cmd,e,a))
    sudo("gzip /var/log/cassandra_log_*" )
    print "\nCassandra logs are saved in /var/log/cassandra_log_%s_%s.log.gz of %s" %( e, a , e )
#end get_cassandra_logs

@roles('database')
def get_cassandra_db_files():
    sudo("rm -rf /var/cassandra_log")
    a = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
    d = env.host_string
    e=run('hostname')
    sudo("mkdir -p /var/cassandra_log")
    if detect_ostype() == 'Ubuntu':
        sudo("cp -R /var/lib/cassandra/* /var/cassandra_log")
    else:
        sudo("cp -R /home/cassandra/* /var/cassandra_log")
    sudo("cd /var/cassandra_log; tar -czf cassandra_file_%s_%s.tgz *" %(e,a))
    print "\nCassandra DB files are saved in /var/cassandra_log/cassandra_file_%s_%s.tgz of %s" %( e,a ,e)
#end get_cassandra_db_file

@roles('build')
@task
def attach_logs_cores(bug_id, timestamp=None):
    '''
    Attach the logs, core-files, bt and contrail-version to a specified location
    '''
    build= env.roledefs['build'][0]
    if timestamp:
        folder= '%s/%s' %( bug_id, timestamp) 
    else:
        time_str = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
        folder='%s/%s' %(bug_id, time_str)
    local('mkdir -p %s' % ( folder ) )
    execute(tar_logs_cores)
    execute(get_cassandra_logs)
    execute(get_cassandra_db_files)
    with hide('everything'):
        for host in env.roledefs['all']:
            with settings( host_string= host, password= env.passwords[host], warn_only=True):
                get('/var/log/logs_*.tgz', '%s/' %( folder ) )
                get('/var/crashes/*gz', '%s/' %( folder ) )
                get('/var/log/gdb_*.log','%s/' %( folder ) )
                get('/var/log/contrail_version*.log','%s/' %( folder ) )
                get('/var/log/cassandra_log*.gz','%s/' %( folder ) )
                get('/var/cassandra_log/cassandra_file*.tgz','%s/' %( folder ) ) 

    print "\nAll logs and cores are saved in %s of %s" %(folder, env.host) 
#end attach_logs_cores
