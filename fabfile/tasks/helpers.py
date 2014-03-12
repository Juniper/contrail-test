import sys
import socket
import os
import time
import collections

from fabfile.config import *
import fabfile.common as common
from fabfile.utils.host import *
from fabfile.utils.multitenancy import *
from fabfile.utils.fabos import *
import datetime

@task
@parallel
@roles('compute')
def compute_reboot():
    reboot_node(env.host_string)

@task
def reboot_node(*args):
    for host_string in args:
        user, hostip = host_string.split('@')
        with settings(hide('running'), host_string=host_string, warn_only=True):
            #Fabric hangs when reboot --force is issued, so adding timeout
            #as workaround.
            try:
                sudo("/etc/contrail/contrail_reboot", timeout=5)
            except CommandTimeout:
                pass

        print 'Reboot issued; Waiting for the node (%s) to go down...' % hostip
        common.wait_until_host_down(wait=300, host=hostip)
        print 'Node (%s) is down... Waiting for node to come back' % hostip
        sys.stdout.write('.')
        while not verify_sshd(hostip,
                              user,
                              env.passwords[host_string]):
            sys.stdout.write('.')
            sleep(2)
            continue
#end compute_reboot

@roles('build')
@task
def all_reimage(build_param="@LATEST"):
    for host in env.roledefs["all"]:
        for i in range(5):
            try:
                hostname = socket.gethostbyaddr( hstr_to_ip(host) )[0].split('.')[0]
            except socket.herror: 
                sleep(5)
                continue
            else:
                break

        if 'ostypes' in env.keys():
            if 'xen' in env.ostypes[host]:
                if env.xen_ver == '6.2':
                    #XenServer 6.2
                    local("/cs-shared/cf/bin/xen62.reimage %s" %(hostname))
                else:
                    #XenServer 6.1
                    local("/cs-shared/cf/bin/xen.reimage %s" %(hostname))
            elif 'fedora' in env.ostypes[host]:
                # Fedora
                local("/cs-shared/cf/bin/reimage %s %s" %(hostname, build_param))
            elif 'ubuntu' in env.ostypes[host]:
                local("/cs-shared/cf/bin/ubuntu.reimage %s" %(hostname))
            else:
                # CentOS
                local("/cs-shared/cf/bin/centos.reimage %s %s" %(hostname, build_param))
        else:
            # CentOS
            local("/cs-shared/cf/bin/centos.reimage %s %s" %(hostname, build_param))
        sleep(1)
#end all_reimage

@roles('compute')
@task
def contrail_version():
    run("contrail-version")

@task
@parallel
@roles('all')
def all_reboot():
    with settings(hide('running'), warn_only=True):
        if env.host_string in env.roledefs['compute']:
            compute_reboot()
        else:
            #Fabric hangs when reboot --force is issued, so adding timeout as
            # workaround.
            try:
                sudo("reboot --force", timeout=5)
            except CommandTimeout:
                pass
#end all_reboot

@task
@roles('build')
def check_ssh():
    sshd_down_hosts = ''
    for host_string in env.roledefs["all"]:
        user, hostip = host_string.split('@')
        password = env.passwords[host_string]
        if not verify_sshd(hostip, user, password):
            sshd_down_hosts += "%s : %s\n" % (host_string, password)

    if sshd_down_hosts: 
        raise Exception("Following list of hosts are down: \n %s" % sshd_down_hosts)
    else:
        print "\n\tAll nodes are Up."
    
@roles('all')
@task
def all_command(command):
    sudo(command)
#end all_command

@roles('all')
@task
def all_ping():
    for host in env.hostnames["all"]:
        local("ping -c 1 -q %s " %(host))
#end all_ping

@roles('all')
@task
def all_version():
    sudo("contrail-version")
#end all_ping

@roles('all')
@task
def all_crash():
    sudo("ls -l /var/crashes")

@roles('control')
@task
def control_crash():
    sudo("ls -l /var/crashes")

@roles('compute')
@task
def compute_crash():
    sudo("ls -l /var/crashes")

@roles('compute')
@task
def compute_provision():
    cfgm_host = env.roledefs['cfgm'][0]
    cfgm_ip = hstr_to_ip(cfgm_host)
    tgt_ip = env.host_string.split('@')[1]
    tgt_hostname = run("hostname")
    prov_args = "--host_name %s --host_ip %s --api_server_ip %s --oper add " \
                                %(tgt_hostname, tgt_ip, cfgm_ip) 
    sudo("/opt/contrail/utils/provision_vrouter.py %s" %(prov_args))


@roles('compute')
@task
def install_img_agent():
    run("yum localinstall %s/extras/contrail-agent*.rpm" %(INSTALLER_DIR))
#end install_img_agent

#@roles('compute')
@task
def test():
    sudo('cd /; ls')

@roles('compute')
@task
def start_vnc():
    run("vncserver")

@roles('cfgm')
@task
def cfgm_status():
    sudo("service contrail-api status")
    sudo("service contrail-schema status")
    sudo("service contrail-discovery status")
    sudo("service contrail-svc-monitor status")
    sudo("service ifmap status")
#end cfgm_status

@roles('cfgm')
@task
def api_restart():
    sudo("service contrail-api restart")
#end api_restart

@roles('cfgm')
@task
def schema_restart():
    sudo("service contrail-schema restart")
#end schema_restart

@roles('database')
@task
def database_restart():
   sudo("service contrail-database restart")
#end database_restart

@roles('database')
@task
def database_status():
    sudo("service contrail-database status")
#end database_status

@roles('control')
@task
def control_restart():
    sudo("service contrail-control restart")
#end control_restart

@roles('control')
@task
def control_status():
    sudo("service contrail-control status")
#end control_status

@roles('compute')
@task
def compute_status():
    run("service openstack-nova-compute status")
    run("service contrail-vrouter status")
#end compute_status

@roles('compute')
@task
def agent_restart():
    run("service contrail-vrouter restart")
#end agent_restart

@roles('cfgm')
@task
def config_demo():
    cfgm_ip = hstr_to_ip(get_control_host_string(env.roledefs['cfgm'][0]))

    with cd(UTILS_DIR):
        run("source /opt/contrail/api-venv/bin/activate && python demo_cfg.py --api_server_ip %s --api_server_port 8082 --public_subnet %s %s" %(cfgm_ip, testbed.public_vn_subnet, get_mt_opts()))
        run("source /opt/contrail/api-venv/bin/activate &&  python add_route_target.py --routing_instance_name default-domain:demo:public:public --route_target_number %s --router_asn %s --api_server_ip %s --api_server_port 8082 %s" \
                    %(testbed.public_vn_rtgt, testbed.router_asn, cfgm_ip, get_mt_opts()))
        run("source /opt/contrail/api-venv/bin/activate &&  python create_floating_pool.py --public_vn_name default-domain:demo:public --floating_ip_pool_name pub_fip_pool --api_server_ip %s --api_server_port 8082 %s" %(cfgm_ip, get_mt_opts()))
        run("source /opt/contrail/api-venv/bin/activate &&  python use_floating_pool.py --project_name default-domain:demo --floating_ip_pool_name default-domain:demo:public:pub_fip_pool --api_server_ip %s --api_server_port 8082 %s" %(cfgm_ip, get_mt_opts()))

#end config_demo


@roles('openstack')
@task
def add_images(image=None):
    mount=None
    if '10.84' in env.host:
        mount= '10.84.5.100'
    elif '10.204' in env.host:
        mount= '10.204.216.51'
    if not mount :
        return 

    images = [ ("turnkey-redmine-12.0-squeeze-x86.vmdk", "redmine-web"),
               ("turnkey-redmine-12.0-squeeze-x86-mysql.vmdk", "redmine-db"),
               ("precise-server-cloudimg-amd64-disk1.img", "ubuntu"),
               ("traffic/ubuntu-traffic.img", "ubuntu-traffic"),
               ("vsrx/junos-vsrx-12.1-in-network.img", "nat-service"),
               ("vsrx/junos-vsrx-12.1-transparent.img", "vsrxbridge"),
               ("ubuntu-netperf.img", "ubuntu-netperf"),
               ("analyzer/analyzer-vm-console.qcow2", "analyzer"),
               ("ddos.qcow2", "ddos"),
               ("demo-ddos.vmdk", "demo-ddos"),
               ("Tier1-LB-Snapshot.qcow2", "Tier1-LB"),
               ("Tier2-Web-Snapshot.qcow2", "Tier2-Web"),
               ("Tier2-DB-Snapshot.qcow2", "Tier2-DB"),
               ("vsrx-fw-no-ping.qcow2", "vsrx-fw-no-ping"),
               ("sugarcrm.vmdk", "sugarcrm") 
             ]

    for (loc, name) in images:
        if image is not None and image != name:
            continue
        local = "/images/"+loc+".gz"
        remote = loc.split("/")[-1]
        remote_gz = remote+".gz"
        run("wget http://%s/%s" % (mount, local)) 
        run("gunzip " + remote_gz)
        if ".vmdk" in loc:
            run("(source /etc/contrail/openstackrc; glance add name='"+name+"' is_public=true container_format=ovf disk_format=vmdk < "+remote+")")
        else:
            run("(source /etc/contrail/openstackrc; glance add name='"+name+"' is_public=true container_format=ovf disk_format=qcow2 < "+remote+")")
        run("rm "+remote)
#end add_images

@roles('openstack')
@task
def add_basic_images(image=None):
    mount=None
    if '10.84' in env.host:
        mount= '10.84.5.100'
    elif '10.204' in env.host:
        mount= '10.204.216.51'
    if not mount :
        return

    images = [ ("precise-server-cloudimg-amd64-disk1.img", "ubuntu"),
               ("traffic/ubuntu-traffic.img", "ubuntu-traffic"),
               ("cirros/cirros-0.3.0-x86_64-uec", "cirros"),
               ("vsrx/junos-vsrx-12.1-in-network.img", "nat-service"),
               ("vsrx/junos-vsrx-12.1-transparent.img", "vsrxbridge"),
               ("analyzer/analyzer-vm-console.qcow2", "analyzer"),
             ]

    for (loc, name) in images:
        if image is not None and image != name:
            continue
        local = "/images/"+loc+".gz"
        remote = loc.split("/")[-1]
        remote_gz = remote+".gz"
        run("wget http://%s/%s" % (mount, local)) 
        run("gunzip " + remote_gz)
        if ".vmdk" in loc:
            run("(source /etc/contrail/openstackrc; glance add name='"+name+"' is_public=true container_format=ovf disk_format=vmdk < "+remote+")")
        elif "cirros" in loc:
            run('source /etc/contrail/openstackrc')
            run('cd /tmp ; sudo rm -f /tmp/cirros-0.3.0-x86_64*')
            run('tar xvf %s -C /tmp/' %remote)
            run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-kernel is_public=true '+
                'container_format=aki disk_format=aki < /tmp/cirros-0.3.0-x86_64-vmlinuz')
            run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-ramdisk is_public=true '+
                    ' container_format=ari disk_format=ari < /tmp/cirros-0.3.0-x86_64-initrd')
            run('source /etc/contrail/openstackrc && glance add name=' +remote+ ' is_public=true '+
                'container_format=ami disk_format=ami '+
                '\"kernel_id=$(glance index | awk \'/cirros-0.3.0-x86_64-kernel/ {print $1}\')\" '+
                '\"ramdisk_id=$(glance index | awk \'/cirros-0.3.0-x86_64-ramdisk/ {print $1}\')\" ' +
                ' < <(zcat --force /tmp/cirros-0.3.0-x86_64-blank.img)')
            run('rm -rf /tmp/*cirros*')
        else:
            run("(source /etc/contrail/openstackrc; glance add name='"+name+"' is_public=true container_format=ovf disk_format=qcow2 < "+remote+")")
        run("rm "+remote)

#end add_basic_images

@roles('compute')
@task
def virsh_cleanup():
    result = sudo("ls /etc/libvirt/qemu/instance*.xml | cut -d '/' -f 5 | cut -d '.' -f 1")
    for inst_name in result.split():
        if re.match('instance', inst_name):
            with settings(warn_only = True):
                sudo('virsh destroy %s' %(inst_name))
                sudo('virsh undefine %s' %(inst_name))
                sudo('rm -rf /var/lib/nova/instances/%s' %(inst_name))
         
#end virsh_cleanup 
@task
def virsh_cmd(cmd):
    result = sudo('virsh %s' %(cmd))
#end virsh_cmd

@task
def sudo_cmd(cmd):
    result = sudo(cmd)
#end sudo_cmd

@roles('cfgm')
@task
def net_list():
    cfgm_ip = hstr_to_ip(env.roledefs['cfgm'][0])

    os_opts = ''
    os_opts = os_opts + ' --os-username %s --os-password %s '\
                          %(testbed.os_username, testbed.os_password)
    os_opts = os_opts + ' --os-tenant-name %s ' %(testbed.os_tenant_name)
    os_opts = os_opts + ' --os-auth-url http://%s:5000/v2.0 ' %(cfgm_ip)

    run('quantum %s net-list' %(os_opts))
#end net_list

@roles('cfgm')
@task
def demo_fixup():
    sudo("service openstack-nova-compute restart")
    sudo("service contrail-schema restart")

@task
def copy(src, dst = '.'):
    put(src, dst)
#end copy

@roles('all')
def cleanup_os_config():
    '''
    This has to be run from reset_config() task only
    '''
    dbs=['nova', 'mysql', 'keystone', 'glance', 'cinder']
    services =['contrail-database','redis', 'mysqld', 'openstack-nova-novncproxy', 'rabbitmq-server', 'ifmap', 'openstack-cinder-volume', 'openstack-cinder-scheduler', 'openstack-cinder-api', 'openstack-glance-registry', 'openstack-glance-api', 'openstack-nova-xvpvncproxy', 'openstack-nova-scheduler', 'openstack-nova-objectstore', 'openstack-nova-metadata-api', 'openstack-nova-consoleauth', 'openstack-nova-console', 'openstack-nova-compute', 'openstack-nova-cert', 'openstack-nova-api', 'contrail-vncserver', 'contrail-analyzer', 'openstack-keystone', 'quantum-server', 'contrail-api', ]
    ubuntu_services =['contrail-database','redis', 'mysql', 'nova-novncproxy', 'rabbitmq-server', 'ifmap', 'cinder-volume', 'cinder-scheduler', 'cinder-api', 'glance-registry', 'glance-api', 'nova-xvpvncproxy', 'nova-scheduler', 'nova-objectstore', 'nova-metadata-api', 'nova-consoleauth', 'nova-console', 'nova-compute', 'nova-cert', 'nova-api', 'contrail-vncserver', 'contrail-analyzer', 'keystone', 'quantum-server', 'contrail-api', 'neutron-server', ]
    # Drop all dbs
    with settings(warn_only=True):
        token=run('cat /etc/contrail/mysql.token')
        for db in dbs:
            run('mysql -u root --password=%s -e \'drop database %s;\''  %(token, db))

        
        if detect_ostype() == 'Ubuntu':
            services = ubuntu_services
        for service in services :
            run('sudo service %s stop' %(service))

        run('sudo rm -f /etc/contrail/mysql.token')
        run('sudo rm -f /etc/contrail/service.token')
        run('sudo rm -f /etc/contrail/keystonerc')
        run('sudo rm -f /var/lib/glance/images/*')
        run('sudo rm -rf /var/lib/nova/tmp/nova-iptables')
        run('sudo rm -rf /var/lib/libvirt/qemu/instance*')
        run('sudo rm -rf /var/log/libvirt/qemu/instance*')
        run('sudo rm -rf /var/lib/nova/instances/*')
        run('sudo rm -rf /etc/libvirt/nwfilter/nova-instance*')
        run('sudo rm -rf /var/log/libvirt/qemu/inst*')
        run('sudo rm -rf /etc/libvirt/qemu/inst*')
        run('sudo rm -rf /var/lib/nova/instances/_base/*')
        
        if detect_ostype() in ['Ubuntu'] and env.host_string in env.roledefs['openstack']:
            sudo('mysql_install_db --user=mysql --ldata=/var/lib/mysql/')
#end cleanup_os_config

@roles('cfgm')
def api_server_reset(option):
    
    api_config_file = '/etc/contrail/supervisord_config_files/contrail-api.ini'
    
    try :
        if option == "add" :
            run('sudo sed -i \'s/vnc_cfg_api_server.py --conf_file/vnc_cfg_api_server.py --reset_config --conf_file/\' %s' %(api_config_file))
        elif option == 'delete' :
            run('sudo sed -i \'s/vnc_cfg_api_server.py --reset_config/vnc_cfg_api_server.py/\' %s' %(api_config_file))
    except SystemExit as e:
        print "Failure of one or more of these cmds are ok"

@roles('compute')
@task
def start_servers(file_n="traffic_profile.py"):
    file_fabt = os.getcwd() + "/fabfile/testbeds/traffic_fabfile.py"
    file_proft = os.getcwd() + "/fabfile/testbeds/" + file_n

    with settings(warn_only=True):
        put(file_fabt, "/root/fabfile.py")
        put(file_proft, "/root/traffic_profile.py")

        sudo("fab setup_hosts start_servers")

@roles('compute')
@task
def start_clients():
    with settings(warn_only=True):
        sudo("fab setup_hosts start_clients")

# from build we go to each compute node, and from there fab run to each of the
# VMs to start traffic scripts
# testbeds/traffic_fabfile.py is copied to each compute node and is the fab file
# used to run traffic scripts in the VMs
# testbeds/traffic_profile.py describes the connections that are need to be made
# by the traffic scripts - testbeds/traffic_profile_sample.py gives one such example

@roles('build')
@task
def start_traffic():
    execute(start_servers)
    sleep(10)
    execute(start_clients)

@roles('build')
@task
def wait_till_all_up(attempts=90, interval=10, node=None, waitdown=True, contrail_role='all'):
    ''' Waits for given nodes to go down and then comeup within the given attempts.
        Defaults: attempts = 90 retries
                  interval = 10 secs
                  node     = env.roledefs['all']
    '''
    if contrail_role == 'compute':
        nodes = node or env.roledefs['compute']
    else:
        nodes = node or env.roledefs['all']
    nodes = [nodes] if type(nodes) is str else nodes
    #Waits for node to shutdown
    if waitdown != 'False':
        for node in nodes:
            nodeip = node.split('@')[1]
            print 'Waiting for the node (%s) to go down...' %nodeip
            common.wait_until_host_down(host=nodeip, wait=900)

    print 'Given Nodes are down... Waiting for nodes to come back'
    for node in nodes:
        with hide('everything'):
            with settings(host_string=node, timeout=int(interval),
                          connection_attempts=int(attempts),
                          linewise=True, warn_only=True,
                          password=env.passwords[node]): 
                connections.connect(env.host_string)
    return 0

def enable_haproxy():
    ''' For Ubuntu. Set ENABLE=1 in /etc/default/haproxy
    '''
    if detect_ostype() == 'Ubuntu':
        with settings(warn_only=True):
            run("sudo sed -i 's/ENABLED=.*/ENABLED=1/g' /etc/default/haproxy")
#end enable_haproxy    

def qpidd_changes_for_ubuntu():
    '''Qpidd.conf changes for Ubuntu
    '''
    qpid_file = '/etc/qpid/qpidd.conf'
    if detect_ostype() == 'Ubuntu':
        with settings(warn_only=True):
            run("sudo sed -i 's/load-module=\/usr\/lib\/qpid\/daemon\/acl.so/#load-module=\/usr\/lib\/qpid\/daemon\/acl.so/g' %s" %(qpid_file))
            run("sudo sed -i 's/acl-file=\/etc\/qpid\/qpidd.acl/#acl-file=\/etc\/qpid\/qpidd.acl/g' %s" %(qpid_file))
            run("sudo sed -i 's/max-connections=2048/#max-connections=2048/g' %s" %(qpid_file))
            run('grep -q \'auth=no\' %s || echo \'auth=no\' >> %s' %(qpid_file,qpid_file))
            run('service qpidd restart')
#end qpidd_changes_for_ubuntu

@task
def is_pingable(host_string, negate=False, maxwait=900):
    result = 0
    hostip = host_string.split('@')[1]
    starttime = datetime.datetime.now()
    timedelta = datetime.timedelta(seconds=int(maxwait))
    runouput = collections.namedtuple('runouput', 'return_code')
    with settings(host_string=host_string, warn_only=True):
       while True:
            try:
                res = run('ping -q -w 2 -c 1 %s' %hostip)
            except:
                res = runouput(return_code=1)
                
            if res.return_code == 0 and negate == 'False':
                print 'Host (%s) is Pingable'
                break
            elif res.return_code != 0 and negate == 'True':
                               print 'Host (%s) is Down' %hostip
                               break
            elif starttime + timedelta <= datetime.datetime.now():
                print 'Timeout while trying to ping host (%s)' %hostip
                result = 1
                break
            else:
                print 'Retrying...'
                time.sleep(1)
    return result

@task
@roles('all')
def is_reimage_complete(version, maxwait=900):
    is_reimage_complete_node(version, maxwait, env.host_string)

@task
@parallel
def is_reimage_complete_node(version, maxwait, *args):
    for host_string in args:
        user, hostip = host_string.split('@')
        start = datetime.datetime.now()
        td = datetime.timedelta(seconds=int(maxwait))
        with settings(host_string=host_string, warn_only=True):
            if is_pingable(host_string, 'True', maxwait):
                raise RuntimeError('Host (%s) is still up' %hostip)
            print 'Host (%s) is Down, Wait till host comes back' %hostip
            if is_pingable(host_string, 'False', maxwait):
                raise RuntimeError('Host (%s) is still down' %hostip)
            print 'Host (%s) is UP, Wait till SSH is UP in host' %hostip
            while True:
                if not verify_sshd(hostip, user, env.password):
                    raise RuntimeError('Unable to SSH to Host (%s)' %hostip)
                act_version = run('rpm -q --queryformat "%{RELEASE}" contrail-install-packages').split('.')[0]
                if int(version) != int(act_version):
                    print 'Expected Reimaged Version (%s) != Actual Version (%s)' %(
                                        version, act_version)
                    print 'Retrying...'
                else:
                    print 'Host (%s) is reimaged to %s' %(hostip, version)
                    break
                if start + td < datetime.datetime.now():
                    raise RuntimeError('Timeout while waiting for reimage complete')

@roles('openstack')
@task
def increase_ulimits():
    '''
    Increase ulimit in /etc/init.d/mysqld /etc/init/mysql.conf /etc/init.d/rabbitmq-server files
    '''
    if detect_ostype() != 'Ubuntu':
        return
    with settings(warn_only = True):
        run("sed -i '/start|stop)/ a\    ulimit -n 10240' /etc/init.d/mysql") 
        run("sed -i '/start_rabbitmq () {/a\    ulimit -n 10240' /etc/init.d/rabbitmq-server")
        run("sed -i '/umask 007/ a\limit nofile 10240 10240' /etc/init/mysql.conf")
        run("sed -i '/\[mysqld\]/a\max_connections = 2048' /etc/mysql/my.cnf")

@roles('cfgm','database','control','collector')
@task
def increase_limits():
    '''
    Increase limits in /etc/security/limits.conf, sysctl.conf and /etc/contrail/supervisor*.conf files
    '''
    limits_conf = '/etc/security/limits.conf'
    with settings(warn_only = True):
        pattern='^root\s*soft\s*nproc\s*.*'
        line = 'root soft nproc 65535'
        insert_line_to_file(pattern = pattern, line = line,file_name = limits_conf)

        pattern='^*\s*hard\s*nofile\s*.*'
        line = '* hard nofile 65535'
        insert_line_to_file(pattern = pattern, line = line,file_name = limits_conf)

        pattern='^*\s*soft\s*nofile\s*.*'
        line = '* soft nofile 65535'
        insert_line_to_file(pattern = pattern, line = line,file_name = limits_conf)

        pattern='^*\s*hard\s*nproc\s*.*'
        line = '* hard nproc 65535'
        insert_line_to_file(pattern = pattern, line = line,file_name = limits_conf)

        pattern='^*\s*soft\s*nproc\s*.*'
        line = '* soft nofile 65535'
        insert_line_to_file(pattern = pattern, line = line,file_name = limits_conf)

        sysctl_conf = '/etc/sysctl.conf'
        insert_line_to_file(pattern = '^fs.file-max.*',
                line = 'fs.file-max = 65535',file_name = sysctl_conf)
        sudo('sysctl -p')

        sudo('sed -i \'s/^minfds.*/minfds=10240/\' /etc/contrail/supervisor*.conf')

#end increase_limits

def insert_line_to_file(line,file_name,pattern=None):
    with settings(warn_only = True):
        if pattern:
            sudo('sed -i \'/%s/d\' %s' %(pattern,file_name))
        sudo('printf "%s\n" >> %s' %(line, file_name))
#end insert_line_to_file

@roles('build')
@task
def full_mesh_ping_by_name():
    for host in env.roledefs['all']:
        with settings(host_string = host, warn_only = True):
            for hostname in env.hostnames['all']:
                result = run('ping -c 1 %s' %(hostname))
                if not result.succeeded:
                    print '!!! Ping from %s to %s failed !!!' %( host, hostname)
                    exit(1)
    print "All nodes are able to ping each other using hostnames"
#end full_mesh_ping

@roles('build')
@task
def validate_hosts():
    all_hostnames = env.hostnames['all']
    current_hostlist = {}
    current_hosttimes = {}
    
    # Check if the hostnames on the nodes are as mentioned in testbed file
    for host in env.roledefs['all']:
        with settings(host_string = host):
            curr_hostname = run('hostname')
            if not curr_hostname  in all_hostnames:
                print "Hostname of host %s : %s not defined in testbed!!!" %(
                    host, curr_hostname)
                exit(1)
            if not curr_hostname  in current_hostlist.keys() :
                current_hostlist[curr_hostname] = host
            else:
                print "Hostname %s assigned to more than one host" %(curr_hostname)
                print "They are %s and %s" %(hstr_to_ip(host), hstr_to_ip(current_hostlist[curr_hostname]))
                print "Please fix them before continuing!! "
                exit(1)
    
    #Check if env.hostnames['all'] has any spurious entries
    if set(current_hostlist.keys()) != set(env.hostnames['all']):
        print "hostnames['all'] in testbed file does not seem to be correct"
        print "Expected : %s" %(current_hostlist)
        print "Seen : %s" %(env.hostnames['all']) 
        exit(1)
    print "All hostnames are unique and defined in testbed correctly..OK"
    
    #Check if date/time on the hosts are almost the same (diff < 5min)
    for host in env.roledefs['all']:
        with settings(host_string = host):
            current_hosttimes[host] = run('date +%s')
    avg_time = sum(map(int,current_hosttimes.values()))/len(current_hosttimes.values())
    for host in env.roledefs['all']:
        print "Expected date/time on host %s : (approx) %s, Seen : %s" %(
            host,
            datetime.datetime.fromtimestamp(avg_time),
            datetime.datetime.fromtimestamp(float(current_hosttimes[host])))
        if abs(avg_time - int(current_hosttimes[host])) > 300 : 
            print "Time of Host % seems to be not in sync with rest of the hosts" %(host)
            print "Please make sure that the date and time on all hosts are in sync before continuning!!"
            exit(1)

    print "Date and time on all hosts are in sync..OK"
    
    # Check if all hosts are reachable by each other using their hostnames
    execute(full_mesh_ping_by_name)
        
