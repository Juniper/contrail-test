import os
import re
import tempfile

from fabfile.config import *
from fabfile.utils.fabos import *
from fabfile.tasks.helpers import reboot_node

@task
@parallel(pool_size=20)
@roles('all')
def install_rpm_all(rpm):
    """Installs any rpm in all nodes."""
    execute('install_pkg_node', rpm, env.host_string)

@task
@parallel(pool_size=20)
@roles('all')
def install_deb_all(deb):
    """Installs any deb in all nodes."""
    execute('install_pkg_node', deb, env.host_string)

@task
@parallel(pool_size=20)
@roles('all')
def install_pkg_all(deb):
    """Installs any rpm/deb package in all nodes."""
    execute('install_pkg_node', deb, env.host_string)

@task
def install_pkg_node(pkg, *args):
    """Installs any rpm/deb in one node."""
    for host_string in args:
        with settings(host_string=host_string):
           pkg_name = os.path.basename(pkg)
           temp_dir= tempfile.mkdtemp()
           run('mkdir -p %s' % temp_dir)
           put(pkg, '%s/%s' % (temp_dir, pkg_name))
           if pkg.endswith('.rpm'):
               run("yum --disablerepo=* -y localinstall %s/%s" % (temp_dir, pkg_name))
           elif pkg.endswith('.deb'):
               run("dpkg -i %s/%s" % (temp_dir, pkg_name))


def upgrade_rpm(rpm):
    rpm_name = os.path.basename(rpm)
    temp_dir= tempfile.mkdtemp()
    run('mkdir -p %s' % temp_dir)
    put(rpm, '%s/%s' % (temp_dir, rpm_name))
    run("rpm --upgrade --force -v %s/%s" % (temp_dir, rpm_name))

@task
@EXECUTE_TASK
@roles('cfgm')
def upgrade_rpm_cfgm(rpm):
    """Upgrades any rpm in cfgm nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('database')
def upgrade_rpm_database(rpm):
    """Upgrades any rpm in database nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('openstack')
def upgrade_rpm_openstack(rpm):
    """Upgrades any rpm in openstack nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('collector')
def upgrade_rpm_collector(rpm):
    """Upgrades any rpm in collector nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('compute')
def upgrade_rpm_compute(rpm):
    """Upgrades any rpm in compute nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('control')
def upgrade_rpm_control(rpm):
    """Upgrades any rpm in control nodes."""
    upgrade_rpm(rpm)

@task
@EXECUTE_TASK
@roles('webui')
def upgrade_rpm_webui(rpm):
    """Upgrades any rpm in webui nodes."""
    upgrade_rpm(rpm)

@task
@parallel(pool_size=20)
@roles('all')
def upgrade_rpm_all(rpm):
    """Upgrades any rpm in all nodes."""
    upgrade_rpm(rpm)

@roles('build')
@task
def install_and_setup_all():
    """Installs and provisions all the contrail services as per the roles."""
    execute('install_contrail')
    #Clear the connections cache
    connections.clear()
    execute('setup_all')

@task
@EXECUTE_TASK
@roles('all')
def upgrade_pkgs():
    """Upgrades the pramiko and pycrypto packages in all nodes."""
    execute("upgrade_pkgs_node", env.host_string)

@task
@roles('build')
def upgrade_pkgs_without_openstack():
    """Upgrades the pramiko and pycrypto packages in all nodes excluding openstack node."""
    host_strings = env.roledefs['all']
    dummy = [host_strings.remove(openstack_node)
             for openstack_node in env.roledefs['openstack']]
    for host_string in host_strings:
        with settings(host_string=host_string):
            execute("upgrade_pkgs_node", host_string)

@task
def upgrade_pkgs_node(*args):
    """Upgrades the pramiko/pcrypto packages in single or list of nodes. USAGE:fab upgrade_pkgs_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            # This step is required in customer env, becasue they used to call fab
            # commands from one of the node in the cluster(cfgm).
            # Installing packages(python-nova, python-cinder) brings in lower version
            # of python-paramiko(1.7.5), fabric-utils requires 1.9.0 or above.
            # ubuntu does not need this, as pycrypto and paramiko are installed as debian packages. 
            cmd = "sudo easy_install \
                  /opt/contrail/contrail_installer/contrail_setup_utils/pycrypto-2.6.tar.gz;\
                  sudo easy_install \
                  /opt/contrail/contrail_installer/contrail_setup_utils/paramiko-1.11.0.tar.gz"
            if detect_ostype() in ['centos', 'fedora', 'redhat']:
                run(cmd)

def yum_install(rpms):
    cmd = "yum -y --nogpgcheck --disablerepo=* --enablerepo=contrail_install_repo install "
    if detect_ostype() in ['centos', 'fedora', 'redhat']:
        for rpm in rpms:
            run(cmd + rpm)

def apt_install(debs):
    cmd = "DEBIAN_FRONTEND=noninteractive apt-get -y --force-yes --allow-unauthenticated install "
    if detect_ostype() in ['Ubuntu']:
        for deb in debs:
            run(cmd + deb)

@task
@parallel(pool_size=20)
@roles('compute')
def install_interface_name(reboot='True'):
    """Installs interface name package in all nodes defined in compute role."""
    execute("install_interface_name_node", env.host_string, reboot=reboot)

@task
def install_interface_name_node(*args, **kwargs):
    """Installs interface name package in one or list of nodes. USAGE:fab install_interface_name_node:user@1.1.1.1,user@2.2.2.2"""
    if len(kwargs) == 0:
        reboot = 'True'
    else:
        reboot = kwargs['reboot']
    for host_string in args:
        with settings(host_string=host_string):
            rpm = ['contrail-interface-name']
            yum_install(rpm)
            if reboot == 'True':
                execute(reboot_node, env.host_string)

@task
@EXECUTE_TASK
@roles('database')
def install_database():
    """Installs database pkgs in all nodes defined in database."""
    execute("install_database_node", env.host_string)

@task
def install_database_node(*args):
    """Installs database pkgs in one or list of nodes. USAGE:fab install_database_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack-database']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisord-contrail-database.override')
                apt_install(pkg)
            else:
                yum_install(pkg)

@task
@EXECUTE_TASK
@roles('openstack')
def install_openstack():
    """Installs openstack pkgs in all nodes defined in openstack role."""
    execute("install_openstack_node", env.host_string)

@task
def install_openstack_node(*args):
    """Installs openstack pkgs in one or list of nodes. USAGE:fab install_openstack_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack']
            if detect_ostype() == 'Ubuntu':
                apt_install(pkg)
            else:
                yum_install(pkg)

@task
@EXECUTE_TASK
@roles('openstack')
def install_openstack_storage():
    """Installs storage pkgs in all nodes defined in openstack role."""
    if detect_ostype() in ['centos']:
        execute("install_openstack_storage_node", env.host_string)

@task
def install_openstack_storage_node(*args):
    """Installs storage pkgs in one or list of nodes. USAGE:fab install_openstack_storage_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            rpm = ['contrail-openstack-storage']
            yum_install(rpm)

@task
@EXECUTE_TASK
@roles('cfgm')
def install_cfgm():
    """Installs config pkgs in all nodes defined in cfgm role."""
    execute("install_cfgm_node", env.host_string)

@task
def install_cfgm_node(*args):
    """Installs config pkgs in one or list of nodes. USAGE:fab install_cfgm_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack-config']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisor-config.override')
                run('echo "manual" >> /etc/init/neutron-server.override')
                apt_install(pkg)
            else:
                yum_install(pkg)


@task
@EXECUTE_TASK
@roles('control')
def install_control():
    """Installs control pkgs in all nodes defined in control role."""
    execute("install_control_node", env.host_string)

@task
def install_control_node(*args):
    """Installs control pkgs in one or list of nodes. USAGE:fab install_control_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack-control']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisor-control.override')
                run('echo "manual" >> /etc/init/supervisor-dns.override')
                apt_install(pkg)
            else:
                yum_install(pkg)


@task
@EXECUTE_TASK
@roles('collector')
def install_collector():
    """Installs analytics pkgs in all nodes defined in collector role."""
    execute("install_collector_node", env.host_string)

@task
def install_collector_node(*args):
    """Installs analytics pkgs in one or list of nodes. USAGE:fab install_collector_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack-analytics']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisor-analytics.override')
                apt_install(pkg)
            else:
                yum_install(pkg)


@task
@EXECUTE_TASK
@roles('webui')
def install_webui():
    """Installs webui pkgs in all nodes defined in webui role."""
    execute("install_webui_node", env.host_string)

@task
def install_webui_node(*args):
    """Installs webui pkgs in one or list of nodes. USAGE:fab install_webui_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            pkg = ['contrail-openstack-webui']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisor-webui.override')
                apt_install(pkg)
            else:
                yum_install(pkg)


@task
@EXECUTE_TASK
@roles('compute')
def install_vrouter():
    """Installs vrouter pkgs in all nodes defined in vrouter role."""
    execute("install_vrouter_node", env.host_string)

@task
def install_vrouter_node(*args):
    """Installs vrouter pkgs in one or list of nodes. USAGE:fab install_vrouter_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            pkg = ['contrail-openstack-vrouter']
            if detect_ostype() == 'Ubuntu':
                run('echo "manual" >> /etc/init/supervisor-vrouter.override')
                apt_install(pkg)
            else:
                yum_install(pkg)

@task
@EXECUTE_TASK
@roles('compute')
def install_compute_storage():
    """Installs storage pkgs in all nodes defined in compute role."""
    if detect_ostype() in ['centos']:
        execute("install_compute_storage_node", env.host_string)

@task
def install_compute_storage_node(*args):
    """Installs storage pkgs in one or list of nodes. USAGE:fab install_compute_storage_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            rpm = ['contrail-openstack-storage']
            yum_install(rpm)

@task
@EXECUTE_TASK
@roles('all')
def create_install_repo():
    """Creates contrail install repo in all nodes."""
    execute("create_install_repo_node", env.host_string)

@task
@roles('build')
def create_install_repo_without_openstack():
    """Creates contrail install repo in all nodes excluding openstack node."""
    host_strings = env.roledefs['all']
    dummy = [host_strings.remove(openstack_node) 
             for openstack_node in env.roledefs['openstack']]
    for host_string in host_strings:
        with settings(host_string=host_string):
            execute("create_install_repo_node", host_string)

@task
def create_install_repo_node(*args):
    """Creates contrail install repo in one or list of nodes. USAGE:fab create_install_repo_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string, warn_only=True):
            run("sudo /opt/contrail/contrail_packages/setup.sh")

@roles('build')
@task
def install_contrail(reboot='True'):
    """Installs required contrail packages in all nodes as per the role definition.
    """
    execute(create_install_repo)
    execute(install_database)
    execute(install_openstack)
    execute(install_cfgm)
    execute(install_control)
    execute(install_collector)
    execute(install_webui)
    execute(install_vrouter)
    execute(upgrade_pkgs)
    execute(update_keystone_log)
    if getattr(env, 'interface_rename', True) and detect_ostype() in ['Ubuntu']:
        print "Installing interface Rename package and rebooting the system."
        execute(install_interface_name, reboot)

@roles('build')
@task
def install_without_openstack():
    """Installs required contrail packages in all nodes as per the role definition except the openstack.
       User has to install the openstack node with their custom openstack pakckages.
    """
    execute(create_install_repo_without_openstack)
    execute(install_database)
    execute(install_cfgm)
    execute(install_control)
    execute(install_collector)
    execute(install_webui)
    execute(install_vrouter)
    execute(upgrade_pkgs_without_openstack)
    if getattr(env, 'interface_rename', True) and detect_ostype() in ['Ubuntu']:
        print "Installing interface Rename package and rebooting the system."
        execute(install_interface_name)

@roles('openstack')
@task
def update_keystone_log():
    """Temporary workaround to update keystone log"""
    #TODO This is a workaround. Need to be fixed as part of package install
    if detect_ostype() in ['Ubuntu']:
        with  settings(warn_only=True):
            run("touch /var/log/keystone/keystone.log")
            run("sudo chown keystone /var/log/keystone/keystone.log")
            run("sudo chgrp keystone /var/log/keystone/keystone.log")


@roles('build')
@task
def copy_install_pkgs(pkgs):
     try:
         pkg_dir = env.pkg_dir
     except:
         pkg_dir = None

     if pkg_dir == None:
         all_pkgs = pkgs.split()
     else:
         all_pkgs = []
         for pkg in pkgs.split():
             all_pkgs.extend(glob.glob('%s/%s' %(pkg_dir, pkg)))

     for pkg in all_pkgs:
         tgt_hosts = []
         if re.match('.*contrail-api', pkg):
             tgt_hosts = env.roledefs['cfgm']
         elif re.match('.*contrail-control', pkg):
             tgt_hosts = env.roledefs['control']
         elif re.match('.*contrail-agent', pkg):
             tgt_hosts = env.roledefs['compute']
         elif re.match('.*contrail-analytics', pkg):
             tgt_hosts = env.roledefs['collector']
         elif re.match('.*contrail-setup', pkg):
             tgt_hosts = env.roledefs['all']

         for tgt_host in tgt_hosts:
             copy_pkg(tgt_host, pkg)
             install_pkg(tgt_host, pkg)
#end copy_install_pkgs

@roles('all')
@task
def uninstall_contrail(full=False):
    '''
    Uninstall contrail and openstack packages so that 
    a fresh installation can be done. 
    
    Note that contrail-install-packages package is still 
    retained so that a new install/setup can be run using : 
        fab install_contrail
        fab setup_all
    
    To force a full cleanup, set full=True as argument. 
    This will remove contrail-install-packages as well
    '''
    run('sudo yum --disablerepo=* --enablerepo=contrail_install_repo -y remove contrail-control contrail-dns openstack-nova openstack-quantum openstack-cinder openstack-glance openstack-keystone openstack-quantum-contrail mysql qpid-cpp-server openstack-dashboard mysql-server openstack-nova-novncproxy zookeeper zookeeper-lib irond contrail-webui contrail-analytics contrail-libs contrail-analytics-venv contrail-api-extension contrail-api-venv contrail-control-venv  contrail-database contrail-nodejs contrail-vrouter-venv contrail-setup openstack-utils redis contrail-openstack-* contrail-database-venv nodejs java java-1.7.0-openjdk libvirt contrail-vrouter euca2ools cassandra django-horizon django-staticfiles python-bitarray python-boto python-thrift libvirt-python libvirt-client python-django-openstack-auth memcached haproxy')
    
    run('sudo yum --disablerepo=* --enablerepo=contrail_install_repo -y remove *openstack* *quantum* *nova* *glance* *keystone* *cinder*')
    with cd('/etc/'):
        run('sudo rm -rf zookeeper glance/ cinder/ openstack_dashboard/ keystone/ quantum/ nova/ irond haproxy')
        run('sudo rm -rf libvirt')
        with settings(warn_only=True):
            run('find ./contrail/* ! -iname \'contrail_ifrename.sh\' -delete')
    with cd('/var/lib/'):
        run('sudo rm -rf nova quantum glance quantum cassandra zookeeper keystone redis mysql haproxy')
        run('sudo rm -rf /usr/share/cassandra /var/cassandra_log /var/crashes /home/cassandra')
        run('sudo rm -rf /var/log/cassandra /var/log/zookeeper /var/run/keystone /opt/contrail/api-venv')
    with cd('/opt/contrail'):
        run('sudo rm -rf api-venv analytics-venv control-venv vrouter-venv database-venv nodejs*')
    with cd('/var/run'):
        run('sudo rm -rf cinder glance quantum nova keystone')
    with cd('/usr/share'):
        run('sudo rm -rf irond')
    with cd('/var/log'):
        run('sudo rm -rf contrail/* nova quantum glance cinder /root/keystone-signing /tmp/keystone-signing /tmp/keystone-signing-nova')
    if full:
        run('sudo yum --disablerepo=* --enablerepo=contrail_install_repo -y remove contrail-install-packages contrail-fabric-utils contrail-setup')
        run('sudo rm -rf /opt/contrail')
#    run('rm -f /etc/sysconfig/network-scripts/ifcfg-p*p*p*')
    with settings(warn_only=True):
        run('reboot')
#end uninstall_contrail

