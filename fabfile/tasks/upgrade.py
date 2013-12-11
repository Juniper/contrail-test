import os

from fabfile.config import *
from fabfile.tasks.services import *
from fabfile.tasks.helpers import compute_reboot, reboot_node
from fabfile.tasks.provision import setup_vrouter, setup_vrouter_node
from fabfile.tasks.install import install_rpm_all, create_install_repo,\
     create_install_repo_node, upgrade_pkgs, install_rpm_node

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

@task
def upgrade():
    run('yum clean all')
    #run('yum --setopt=tsflags=noscripts -y --disablerepo=* --enablerepo=contrail_install_repo update')
    run('yum -y --disablerepo=* --enablerepo=contrail_install_repo update')
    
@task
def upgrade_venv_packages():
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
def upgrade_database(rpm):
    """Upgrades the contrail database pkgs in all nodes defined in database."""
    execute("upgrade_database_node", rpm, env.host_string)

@task
def upgrade_database_node(rpm, *args):
    """Upgrades database pkgs in one or list of nodes. USAGE:fab upgrade_database_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('uninstall_database_node', host_string)
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_database)

@task
@EXECUTE_TASK
@roles('openstack')
def upgrade_openstack(rpm):
    """Upgrades openstack pkgs in all nodes defined in openstack role."""
    execute("upgrade_openstack_node", rpm, env.host_string)

@task
def upgrade_openstack_node(rpm, *args):
    """Upgrades openstack pkgs in one or list of nodes. USAGE:fab upgrade_openstack_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_openstack)


@task
@EXECUTE_TASK
@roles('cfgm')
def upgrade_cfgm(rpm):
    """Upgrades config pkgs in all nodes defined in cfgm role."""
    execute("upgrade_cfgm_node", rpm, env.host_string)

@task
def upgrade_cfgm_node(rpm, *args):
    """Upgrades config pkgs in one or list of nodes. USAGE:fab upgrade_cfgm_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_cfgm)


@task
@EXECUTE_TASK
@roles('control')
def upgrade_control(rpm):
    """Upgrades control pkgs in all nodes defined in control role."""
    execute("upgrade_control_node", rpm, env.host_string)

@task
def upgrade_control_node(rpm, *args):
    """Upgrades control pkgs in one or list of nodes. USAGE:fab upgrade_control_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_control)


@task
@EXECUTE_TASK
@roles('collector')
def upgrade_collector(rpm):
    """Upgrades analytics pkgs in all nodes defined in collector role."""
    execute("upgrade_collector_node", rpm, env.host_string)

@task
def upgrade_collector_node(rpm, *args):
    """Upgrades analytics pkgs in one or list of nodes. USAGE:fab upgrade_collector_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_collector)


@task
@EXECUTE_TASK
@roles('webui')
def upgrade_webui(rpm):
    """Upgrades webui pkgs in all nodes defined in webui role."""
    execute("upgrade_webui_node", rpm, env.host_string)

@task
def upgrade_webui_node(rpm, *args):
    """Upgrades webui pkgs in one or list of nodes. USAGE:fab upgrade_webui_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('upgrade_pkgs_node', host_string)
            execute(restart_webui)


@task
@EXECUTE_TASK
@roles('compute')
def upgrade_vrouter(rpm):
    """Upgrades vrouter pkgs in all nodes defined in vrouter role."""
    execute("upgrade_vrouter_node", rpm, env.host_string)

@task
def upgrade_vrouter_node(rpm, *args):
    """Upgrades vrouter pkgs in one or list of nodes. USAGE:fab upgrade_vrouter_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        with  settings(host_string=host_string):
            execute('backup_install_repo_node', host_string)
            execute('install_rpm_node', rpm, host_string)
            execute('create_install_repo_node', host_string)
            execute(upgrade)
            execute(upgrade_venv_packages)
            execute('setup_vrouter_node', host_string)

@task
@EXECUTE_TASK
@roles('all')
def upgrade_all(rpm):
    """Upgrades all the contrail rpms in all nodes."""
    execute(uninstall_database)
    execute(backup_install_repo)
    execute('install_rpm_all', rpm)
    execute(create_install_repo)
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
def upgrade_contrail(rpm):
    """Upgrades all the  contrail packages in all nodes as per the role definition.
    """
    if len(env.roledefs['all']) == 1:
        execute('upgrade_all', rpm)
    else:
        execute('upgrade_database', rpm)
        execute('upgrade_openstack', rpm)
        execute('upgrade_cfgm', rpm)
        execute('upgrade_control', rpm)
        execute('upgrade_collector', rpm)
        execute('upgrade_webui', rpm)
        execute('upgrade_vrouter', rpm)
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
