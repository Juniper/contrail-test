import uuid

from fabfile.config import *
from fabfile.utils.fabos import detect_ostype


def verfiy_and_update_hosts(host_name):
    host_name = run('hostname')
    resolved = run("ping -c 1 %s | grep '1 received'" % host_name)
    if not resolved:
        run("echo '%s          %s' >> /etc/hosts" % (host_string.split('@')[1], host_name))

@task
@parallel
@roles('cfgm')
def set_guest_user_permissions():
    with settings(warn_only=True):
        run('rabbitmqctl set_permissions guest ".*" ".*" ".*"')

@task
@parallel
@roles('cfgm')
def config_rabbitmq():
    if detect_ostype() in ['centos']:
        rabbit_conf = '/etc/rabbitmq/rabbitmq.config'
        run('sudo echo "[" > %s' % rabbit_conf)
        run("sudo echo '   {rabbit, [ {tcp_listeners, [{\"0.0.0.0\", 5672}]} ]' >> %s" % rabbit_conf)
        run('sudo echo "    }" >> %s' % rabbit_conf)
        run('sudo echo "]." >> %s' % rabbit_conf)

@task
@parallel
@roles('cfgm')
def allow_rabbitmq_port():
    if detect_ostype() in ['centos']:
        run("iptables --flush")
        run("service iptables save")

@task
@parallel
@roles('cfgm')
def stop_rabbitmq_and_set_cookie(uuid):
     with settings(warn_only=True):
         run("service rabbitmq-server stop")
         run("epmd -kill")
     run("echo '%s' > /var/lib/rabbitmq/.erlang.cookie" % uuid)


@task
@parallel
@roles('cfgm')
def start_rabbitmq():
     run("service rabbitmq-server start")

@task
@parallel
@roles('cfgm')
def rabbitmqctl_stop_app():
    run("rabbitmqctl stop_app")

@task
@parallel
@roles('cfgm')
def rabbitmqctl_reset():
    run("rabbitmqctl force_reset")

@task
@parallel
@hosts(*env.roledefs['cfgm'][1:])
def rabbitmqctl_start_app():
    execute("rabbitmqctl_start_app_node", env.host_string)

@task
def rabbitmqctl_start_app_node(*args):
    for host_string in args:
        with settings(host_string=host_string):
            run("rabbitmqctl start_app")

@task
@roles('cfgm')
def verify_cfgm_hostname():
    for host_string in env.roledefs['cfgm']:
        with settings(host_string=host_string):
            host_name = run('hostname')
        verfiy_and_update_hosts(host_name)

@task
@hosts(*env.roledefs['cfgm'][1:])
def add_cfgm_to_rabbitmq_cluster():
    with settings(host_string=env.roledefs['cfgm'][0]):
        cfgm1 = run('hostname')
    this_cfgm = run('hostname')
    if detect_ostype() in ['Ubuntu']:
        run("rabbitmqctl cluster rabbit@%s rabbit@%s" % (cfgm1, this_cfgm))
    else:
        run("rabbitmqctl join_cluster --ram rabbit@%s" % cfgm1)

@task
@roles('cfgm')
def verify_cluster_status():
    output = run("rabbitmqctl cluster_status")
    
    cfgms = []
    for host_string in env.roledefs['cfgm']:
        with settings(host_string=host_string):
            host_name = run('hostname')
            cfgms.append('rabbit@%s' % host_name)
    for cfgm in cfgms:
        if cfgm+',' not in output and cfgm+']' not in output:
            print "RabbitMQ cluster is not setup properly"
            exit(1)


@task
@roles('build')
def setup_rabbitmq_cluster():
    execute('stop_cfgm')
    if len(env.roledefs['cfgm']) <= 1:
        print "Single cfgm cluster, skipping rabbitmq cluster setup."
        return 
    rabbitmq_cluster_uuid = getattr(testbed, 'rabbitmq_cluster_uuid', None)
    if not rabbitmq_cluster_uuid:
        rabbitmq_cluster_uuid = uuid.uuid4()

    execute(verify_cfgm_hostname)
    execute(allow_rabbitmq_port)
    execute(config_rabbitmq)
    execute("stop_rabbitmq_and_set_cookie", rabbitmq_cluster_uuid)
    execute(start_rabbitmq)
    execute(rabbitmqctl_stop_app)
    execute(rabbitmqctl_reset)
    execute("rabbitmqctl_start_app_node", env.roledefs['cfgm'][0])
    execute(add_cfgm_to_rabbitmq_cluster)
    execute(rabbitmqctl_start_app) 
    execute(verify_cluster_status)
