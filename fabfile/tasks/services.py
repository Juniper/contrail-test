from fabfile.config import *
from misc import zoolink
from fabfile.utils.fabos import detect_ostype

@task
def stop_and_disable_qpidd():
    """stops the qpidd and disables it."""
    execute(stop_and_disable_qpidd_node, env.host_string)

@task
def stop_and_disable_qpidd_node(*args):
    """stops the qpidd and disables it in one node."""
    for host_string in args:
        with settings(host_string=host_string, warn_only=True):
            if not run('service qpidd status').succeeded:
                print "qpidd not running, skipping stop."
                return
        with settings(host_string=host_string):
            run('service qpidd stop')
            run('chkconfig qpidd off')

@task
@roles('database')
def stop_database():
    """stops the contrail database services."""
    run('service supervisord-contrail-database stop')

@task
@roles('cfgm')
def stop_cfgm():
    """stops the contrail config services."""
    with settings(warn_only=True):
        run('service supervisor-config stop')

@task
@roles('cfgm')
def start_cfgm():
    """starts the contrail config services."""
    with settings(warn_only=True):
        run('service supervisor-config start')

@task
@task
@roles('control')
def stop_control():
    """stops the contrail control services."""
    run('service supervisor-control stop')

@task
@roles('collector')
def stop_collector():
    """stops the contrail collector services."""
    run('service supervisor-analytics stop')
    run('service contrail-collector stop')
    run('service contrail-opserver stop')
    run('service contrail-qe stop')
    run('service redis-query stop')
    run('service redis-uve stop')

@task
@roles('compute')
def stop_vrouter():
    """stops the contrail vrouter services."""
    run('service supervisor-vrouter stop')

@task
@roles('webui')
def stop_webui():
    """stops the contrail webui services."""
    run('service supervisor-webui stop')

@task
@roles('database')
def restart_database():
    """Restarts the contrail database services."""
    execute('restart_database_node', env.host_string)

@task
def restart_database_node(*args):
    """Restarts the contrail database services in once database node. USAGE:fab restart_database_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            run('service supervisord-contrail-database restart')

@task
@roles('openstack')
def restart_openstack():
    """Restarts the contrail openstack services."""
    execute('restart_openstack_node', env.host_string)

@task
def restart_openstack_node(*args):
    """Restarts the contrail openstack services in once openstack node. USAGE:fab restart_openstack_node:user@1.1.1.1,user@2.2.2.2"""
    openstack_services = ['rabbitmq-server', 'httpd', 'memcached', 'openstack-nova-api',
                          'openstack-nova-scheduler', 'openstack-nova-cert',
                          'openstack-nova-consoleauth', 'openstack-nova-novncproxy',
                          'openstack-nova-conductor', 'openstack-nova-compute']
    if detect_ostype() in ['Ubuntu']:
        openstack_services = ['rabbitmq-server', 'memcached', 'nova-api',
                              'nova-scheduler', 'glance-api',
                              'glance-registry', 'keystone',
                              'nova-conductor', 'cinder-api', 'cinder-scheduler']

    for host_string in args:
        with  settings(host_string=host_string):
            for svc in openstack_services:   
                run('service %s restart' % svc)

@task
@roles('compute')
def restart_openstack_compute():
    """Restarts the contrail openstack compute service."""
    if detect_ostype() in ['Ubuntu']:
        run('service nova-compute restart')
        return
    run('service openstack-nova-compute restart')

@task
@parallel
@roles('cfgm')
def restart_cfgm():
    """Restarts the contrail config services."""
    execute("restart_cfgm_node", env.host_string)

@task
def restart_cfgm_node(*args):
    """Restarts the contrail config services in once cfgm node. USAGE:fab restart_cfgm_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            execute('zoolink_node', host_string)
            run('service contrail-zookeeper restart')
    sleep(5)

    for host_string in args:
        with  settings(host_string=host_string):
            run('supervisorctl -s http://localhost:9004 restart contrail-config-nodemgr')
            run('service ifmap restart')
            run('supervisorctl -s http://localhost:9004 restart contrail-api:0')
            run('supervisorctl -s http://localhost:9004 restart contrail-discovery:0')
            run('service contrail-schema restart')
            run('service contrail-svc-monitor restart')
            #run('service redis-config restart')

@task
@roles('control')
def restart_control():
    """Restarts the contrail control services."""
    execute("restart_control_node", env.host_string)

@task
def restart_control_node(*args):
    """Restarts the contrail control services in once control node. USAGE:fab restart_control_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            run('service supervisor-control restart')

@task
@roles('collector')
def restart_collector():
    """Restarts the contrail collector services."""
    execute('restart_collector_node', env.host_string)

@task
def restart_collector_node(*args):
    """Restarts the contrail collector services in once collector node. USAGE:fab restart_collector_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            run('service supervisor-analytics restart')

@task
@roles('compute')
def restart_vrouter():
    """Restarts the contrail compute services."""
    execute('restart_vrouter_node', env.host_string)

@task
def restart_vrouter_node(*args):
    """Restarts the contrail vrouter services in once vrouter node. USAGE:fab restart_vrouter_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            run('service supervisor-vrouter restart')

@task
@roles('webui')
def restart_webui():
    """Restarts the contrail webui services."""
    execute('restart_webui_node', env.host_string)

@task
def restart_webui_node(*args):
    """Restarts the contrail webui services in once webui node. USAGE:fab restart_webui_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            run('service supervisor-webui restart')
