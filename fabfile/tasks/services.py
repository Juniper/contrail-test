from fabfile.config import *
from misc import zoolink

@task
@roles('database')
def stop_database():
    """stops the contrail database services."""
    run('service supervisord-contrail-database stop')

@task
@roles('cfgm')
def stop_cfgm():
    """stops the contrail config services."""
    run('service supervisor-config stop')

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
    """startops the contrail database services."""
    run('service supervisord-contrail-database restart')

@task
@roles('openstack')
def restart_openstack():
    """startops the contrail openstack services."""
    openstack_services = ['qpidd', 'httpd', 'memcached', 'openstack-nova-api',
                          'openstack-nova-scheduler', 'openstack-nova-cert',
                          'openstack-nova-consoleauth', 'openstack-nova-novncproxy',
                          'openstack-nova-conductor', 'openstack-nova-compute']
    for svc in openstack_services:   
        run('service %s restart' % svc)

@task
@roles('compute')
def restart_openstack_compute():
    """startops the contrail openstack compute service."""
    run('service openstack-nova-compute restart')

@task
@roles('cfgm')
def restart_cfgm():
    """starts the contrail config services."""
    execute('zoolink')
    run('service supervisor-config restart')

@task
@roles('control')
def restart_control():
    """starts the contrail control services."""
    # Use stop/start instead of restart due to bug 2152
    #run('service supervisor-control restart')
    run('service supervisor-control stop')
    run('service supervisor-control start')

@task
@roles('collector')
def restart_collector():
    """starts the contrail collector services."""
    run('service supervisor-analytics restart')

@task
@roles('compute')
def restart_vrouter():
    """starts the contrail compute services."""
    run('service supervisor-vrouter restart')

@task
@roles('webui')
def restart_webui():
    """starts the contrail webui services."""
    run('service supervisor-webui restart')
