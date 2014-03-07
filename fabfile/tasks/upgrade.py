import os

from fabfile.utils.fabos import *
from fabfile.config import *
from fabfile.tasks.services import *
from fabfile.tasks.helpers import compute_reboot, reboot_node
from fabfile.tasks.provision import setup_vrouter, setup_vrouter_node
from fabfile.tasks.install import install_pkg_all, create_install_repo,\
     create_install_repo_node, upgrade_pkgs, install_pkg_node

RELEASES_WITH_QPIDD = ('1.0', '1.01', '1.02', '1.03')

@task
@EXECUTE_TASK
@roles('database')
def uninstall_database():
    execute("uninstall_database_node", env.host_string)

@task
def uninstall_database_node(*args):
    for host_string in args:
        with  settings(host_string=host_string):
            contrail_database_ver = run("rpm -q --queryformat '%{VERSION}' contrail-database")
            if contrail_database_ver == '1.02':
                execute("stop_database")
                #delete old version, this will erase contrail-database & contrail-openstack-database
                run("yum -y --disablerepo=* --enablerepo=contrail_install_repo erase contrail-database")
                #install new version, this will install contrail-database & contrail-openstack-database
                #start will happen later after update of all other packages
                run('yum -y --disablerepo=* --enablerepo=contrail_install_repo install contrail-openstack-database')
            elif contrail_database_ver == '1.0':
                execute("stop_database")
                #delete old version, 1.0 version the PREUN script does not run and yum erase fails
                #following commands helps overcome that
                run('yum -y --disablerepo=* --enablerepo=contrail_install_repo erase contrail-openstack-database')
                run('rpm --erase --nopreun contrail-database')
                #install new version, start will happen later after update of all other packages
                run('yum -y --disablerepo=* --enablerepo=contrail_install_repo install contrail-openstack-database')

def yum_upgrade():
    run('yum clean all')
    run('yum -y --disablerepo=* --enablerepo=contrail_install_repo update')

def apt_upgrade():
    run(' apt-get clean')
    rls = get_release()
    if '1.04' in rls:
        #Hack to solve the webui config file issue
        cmd = "yes N | DEBIAN_FRONTEND=noninteractive apt-get -y --force-yes upgrade"
    else:
        cmd = "DEBIAN_FRONTEND=noninteractive apt-get -y --force-yes upgrade"
    run(cmd)
    
@task
def upgrade():
    if detect_ostype() in ['centos', 'fedora']:
        yum_upgrade()
    elif detect_ostype() in ['Ubuntu']:
        apt_upgrade()

@task
def upgrade_api_venv_packages():
    pip_cmd = "pip install -U -I --force-reinstall --no-deps --index-url=''"
    run('chmod +x /opt/contrail/api-venv/bin/pip')
    run("source /opt/contrail/api-venv/bin/activate && %s /opt/contrail/api-venv/archive/*" % pip_cmd)

@task
def upgrade_venv_packages():
    if detect_ostype() in ['Ubuntu']:
        print "Not requried as ubuntu-contrail has no virtual enviroinment." 
        return
    pip_cmd = "pip install -U -I --force-reinstall --no-deps --index-url=''"
    run('chmod +x /opt/contrail/api-venv/bin/pip')
    run('chmod +x /opt/contrail/analytics-venv/bin/pip')
    run('chmod +x /opt/contrail/vrouter-venv/bin/pip')
    run('chmod +x /opt/contrail/control-venv/bin/pip')
    run('chmod +x /opt/contrail/database-venv/bin/pip')
    run("source /opt/contrail/api-venv/bin/activate && %s /opt/contrail/api-venv/archive/*" % pip_cmd)
    run("source /opt/contrail/analytics-venv/bin/activate && %s /opt/contrail/analytics-venv/archive/*" % pip_cmd)
    run("source /opt/contrail/vrouter-venv/bin/activate && %s /opt/contrail/vrouter-venv/archive/*" % pip_cmd)
    run("source /opt/contrail/control-venv/bin/activate && %s /opt/contrail/control-venv/archive/*" % pip_cmd)
    run("source /opt/contrail/database-venv/bin/activate && %s /opt/contrail/database-venv/archive/*" % pip_cmd)

@task
@EXECUTE_TASK
@roles('database')
def upgrade_database(pkg):
    """Upgrades the contrail database pkgs in all nodes defined in database."""
    execute("upgrade_database_node", pkg, env.host_string)

@task
def upgrade_database_node(pkg, *args):
    """Upgrades database pkgs in one or list of nodes. USAGE:fab upgrade_database_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            if detect_ostype() in ['centos', 'fedora']:
                execute('uninstall_database_node', host_string)
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_database_node', host_string)

@task
@EXECUTE_TASK
@roles('openstack')
def upgrade_openstack(pkg):
    """Upgrades openstack pkgs in all nodes defined in openstack role."""
    execute("upgrade_openstack_node", pkg, env.host_string)

@task
def upgrade_openstack_node(pkg, *args):
    """Upgrades openstack pkgs in one or list of nodes. USAGE:fab upgrade_openstack_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_api_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_openstack_node', host_string)


@task
@EXECUTE_TASK
@roles('cfgm')
def upgrade_cfgm(pkg):
    """Upgrades config pkgs in all nodes defined in cfgm role."""
    execute("upgrade_cfgm_node", pkg, env.host_string)

@task
def upgrade_cfgm_node(pkg, *args):
    """Upgrades config pkgs in one or list of nodes. USAGE:fab upgrade_cfgm_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_cfgm_node', host_string)


@task
@EXECUTE_TASK
@roles('control')
def upgrade_control(pkg):
    """Upgrades control pkgs in all nodes defined in control role."""
    execute("upgrade_control_node", pkg, env.host_string)

@task
def upgrade_control_node(pkg, *args):
    """Upgrades control pkgs in one or list of nodes. USAGE:fab upgrade_control_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)

            # If necessary, migrate to new ini format based configuration.
            if os.path.exists('/opt/contrail/contrail_installer/contrail_config_templates/control-node.conf.sh'):
                run("/opt/contrail/contrail_installer/contrail_config_templates/control-node.conf.sh")
            if os.path.exists('/opt/contrail/contrail_installer/contrail_config_templates/dns.conf.sh'):
                run("/opt/contrail/contrail_installer/contrail_config_templates/dns.conf.sh")
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_control_node', host_string)


@task
@EXECUTE_TASK
@roles('collector')
def upgrade_collector(pkg):
    """Upgrades analytics pkgs in all nodes defined in collector role."""
    execute("upgrade_collector_node", pkg, env.host_string)

@task
def upgrade_collector_node(pkg, *args):
    """Upgrades analytics pkgs in one or list of nodes. USAGE:fab upgrade_collector_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_collector_node', host_string)


@task
@EXECUTE_TASK
@roles('webui')
def upgrade_webui(pkg):
    """Upgrades webui pkgs in all nodes defined in webui role."""
    execute("upgrade_webui_node", pkg, env.host_string)

@task
def upgrade_webui_node(pkg, *args):
    """Upgrades webui pkgs in one or list of nodes. USAGE:fab upgrade_webui_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute('restart_webui_node', host_string)


@task
@EXECUTE_TASK
@roles('compute')
def upgrade_vrouter(pkg):
    """Upgrades vrouter pkgs in all nodes defined in vrouter role."""
    execute("upgrade_vrouter_node", pkg, env.host_string)

@task
def upgrade_vrouter_node(pkg, *args):
    """Upgrades vrouter pkgs in one or list of nodes. USAGE:fab upgrade_vrouter_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_pkg_node', pkg, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('setup_vrouter_node', host_string)

@task
@EXECUTE_TASK
@roles('all')
def upgrade_all(pkg):
    """Upgrades all the contrail pkgs in all nodes."""
    if detect_ostype() in ['centos', 'fedora']:
        execute(uninstall_database)
    execute(backup_install_repo)
    execute('install_pkg_all', pkg)
    execute(create_install_repo)
    execute(check_and_stop_disable_qpidd_in_openstack)
    execute(check_and_stop_disable_qpidd_in_cfgm)
    execute(upgrade)
    execute(upgrade_venv_packages)
    execute(upgrade_pkgs)
    execute(restart_database)
    execute(restart_openstack)
    execute(restart_cfgm)
    execute(restart_control)
    execute(restart_collector)
    execute(restart_webui)
    execute(setup_vrouter)
    execute(compute_reboot)
    #Clear the connections cache
    connections.clear()
    execute(restart_openstack_compute)

@roles('build')
@task
def upgrade_contrail(pkg):
    """Upgrades all the  contrail packages in all nodes as per the role definition.
    """
    execute('check_and_kill_zookeeper')
    if len(env.roledefs['all']) == 1:
        execute('upgrade_all', pkg)
    else:
        execute(check_and_stop_disable_qpidd_in_openstack)
        execute(check_and_stop_disable_qpidd_in_cfgm)
        execute('upgrade_database', pkg)
        execute('upgrade_openstack', pkg)
        execute('upgrade_cfgm', pkg)
        execute(check_and_setup_rabbitmq_cluster)
        execute('upgrade_control', pkg)
        execute('upgrade_collector', pkg)
        execute('upgrade_webui', pkg)
        execute('upgrade_vrouter', pkg)
        execute(compute_reboot)
        #Clear the connections cache
        connections.clear()
        execute(restart_openstack_compute)


@roles('build')
@task
def upgrade_without_openstack(pkg):
    """Upgrades all the  contrail packages in all nodes except openstack node as per the role definition.
    """
    execute('check_and_kill_zookeeper')
    execute(check_and_stop_disable_qpidd_in_cfgm)
    execute('upgrade_database', pkg)
    execute('upgrade_cfgm', pkg)
    execute(check_and_setup_rabbitmq_cluster)
    execute('upgrade_control', pkg)
    execute('upgrade_collector', pkg)
    execute('upgrade_webui', pkg)
    execute('upgrade_vrouter', pkg)
    execute(compute_reboot)
    #Clear the connections cache
    connections.clear()
    execute(restart_openstack_compute)

@task
@EXECUTE_TASK
@roles('all')
def backup_install_repo():
    """Backup contrail install repo in all nodes."""
    execute("backup_install_repo_node", env.host_string)

@task
def backup_install_repo_node(*args):
    """Backup contrail install repo in one or list of nodes. USAGE:fab create_install_repo_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            version = run("cat /opt/contrail/contrail_packages/VERSION | cut -d '=' -f2")
            version = version.strip()
            out = run("ls /opt/contrail/")
            if 'contrail_install_repo_%s' % version not in out:
                run("mv /opt/contrail/contrail_install_repo /opt/contrail/contrail_install_repo_%s" % version)

@task
@hosts(env.roledefs['cfgm'][0])
def check_and_setup_rabbitmq_cluster():
    if (get_release('contrail-openstack-config') in RELEASES_WITH_QPIDD and
        get_release() not in RELEASES_WITH_QPIDD):
        execute(setup_rabbitmq_cluster)

@task
@EXECUTE_TASK
@roles('openstack')
def check_and_stop_disable_qpidd_in_openstack():
    if (get_release('contrail-openstack') in RELEASES_WITH_QPIDD and
        get_release() not in RELEASES_WITH_QPIDD):
        execute('stop_and_disable_qpidd_node', env.host_string)

@task
@EXECUTE_TASK
@roles('cfgm')
def check_and_stop_disable_qpidd_in_cfgm():
    if (get_release('contrail-openstack-config') in RELEASES_WITH_QPIDD and
        get_release() not in RELEASES_WITH_QPIDD):
        execute('stop_and_disable_qpidd_node', env.host_string)
