from fabfile.config import *
from fabfile.utils.fabos import *
from fabfile.utils.host import *
from fabfile.utils.interface import *
from fabfile.utils.multitenancy import *
from fabfile.utils.migration import *
from fabfile.utils.storage import *
from fabfile.utils.analytics import *
from fabfile.tasks.install import *
from fabfile.tasks.helpers import *
from fabfile.tasks.tester import setup_test_env

@task
@EXECUTE_TASK
@roles('all')
def bash_autocomplete_systemd():
    host = env.host_string
    output = run('uname -a')
    if 'xen' in output or 'el6' in output:
        pass
    else:
        #Assume Fedora
        sudo("echo 'source /etc/bash_completion.d/systemd-bash-completion.sh' >> /root/.bashrc")

@task
@roles('cfgm')
def setup_cfgm():
    """Provisions config services in all nodes defined in cfgm role."""
    execute("setup_cfgm_node", env.host_string)

@task
def setup_cfgm_node(*args):
    """Provisions config services in one or list of nodes. USAGE: fab setup_cfgm_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        #cfgm_host = env.host_string
        cfgm_host=get_control_host_string(host_string)
        tgt_ip = hstr_to_ip(cfgm_host)
        cfgm_host_password = env.passwords[host_string]

        openstack_host = get_control_host_string(env.roledefs['openstack'][0])
        openstack_ip = hstr_to_ip(openstack_host)

        # Prefer local collector node
        cfgm_host_list=[]
        for entry in env.roledefs['cfgm']:
            cfgm_host_list.append(get_control_host_string(entry))
        if cfgm_host in cfgm_host_list:
            collector_ip = tgt_ip
        else:
            # Select based on index
            hindex = cfgm_host_list.index(cfgm_host)
            hindex = hindex % len(env.roledefs['collector']) 
            collector_host = get_control_host_string(env.roledefs['collector'][hindex])
            collector_ip = hstr_to_ip(collector_host)
        mt_opt = '--multi_tenancy' if get_mt_enable() else ''
        cassandra_ip_list = [hstr_to_ip(get_control_host_string(cassandra_host)) for cassandra_host in env.roledefs['database']]
        cfgm_ip_list = [hstr_to_ip(get_control_host_string(cassandra_host)) for cassandra_host in env.roledefs['cfgm']]
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run("PASSWORD=%s python setup-vnc-cfgm.py --self_ip %s --openstack_ip %s --collector_ip %s %s --cassandra_ip_list %s --zookeeper_ip_list %s --cfgm_index %d %s" %(
                     cfgm_host_password,tgt_ip, openstack_ip, collector_ip, mt_opt, ' '.join(cassandra_ip_list), ' '.join(cfgm_ip_list), cfgm_host_list.index(cfgm_host)+1, get_service_token()))
#end setup_cfgm

@task
@roles('openstack')
def setup_openstack():
    """Provisions openstack services in all nodes defined in openstack role."""
    execute("setup_openstack_node", env.host_string)

@task
def setup_openstack_node(*args):
    """Provisions openstack services in one or list of nodes. USAGE: fab setup_openstack_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        self_host = get_control_host_string(host_string)
        self_ip = hstr_to_ip(self_host)
        openstack_host_password = env.passwords[host_string]

        cfgm_host = get_control_host_string(env.roledefs['cfgm'][0])
        cfgm_ip = hstr_to_ip(cfgm_host)
    
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run("PASSWORD=%s python setup-vnc-openstack.py --self_ip %s --cfgm_ip %s %s" %(
                    openstack_host_password, self_ip, cfgm_ip, get_service_token()))
#end setup_openstack

@task
@roles('collector')
def setup_collector():
    """Provisions collector services in all nodes defined in collector role."""
    execute("setup_collector_node", env.host_string)

@task
def setup_collector_node(*args):
    """Provisions collector services in one or list of nodes. USAGE: fab setup_collector_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        cfgm_host = get_control_host_string(env.roledefs['cfgm'][0])
        cfgm_ip = hstr_to_ip(cfgm_host)
        collector_host_password = env.passwords[host_string]
        collector_host = get_control_host_string(host_string)
        ncollectors = len(env.roledefs['collector'])
        redis_master_host = get_control_host_string(env.roledefs['collector'][0])
        if collector_host == redis_master_host:
            is_redis_master = True
        else:
            is_redis_master = False
        tgt_ip = hstr_to_ip(collector_host)
        cassandra_host_list = [get_control_host_string(cassandra_host) for cassandra_host in env.roledefs['database']]
        if collector_host in cassandra_host_list:
            cassandra_host_list.remove(collector_host)
            cassandra_host_list.insert(0, collector_host)
        cassandra_ip_list = [hstr_to_ip(cassandra_host) for cassandra_host in cassandra_host_list]
        redis_master_ip = hstr_to_ip(redis_master_host)
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run_cmd = "PASSWORD=%s python setup-vnc-collector.py --cassandra_ip_list %s --cfgm_ip %s --self_collector_ip %s --num_nodes %d --redis_master_ip %s --redis_role " \
                           % (collector_host_password, ' '.join(cassandra_ip_list), cfgm_ip, tgt_ip, ncollectors, redis_master_ip) 
                if not is_redis_master:
                    run_cmd += "slave "
                else:
                    run_cmd += "master "
                analytics_database_ttl = get_database_ttl()
                if analytics_database_ttl is not None:
                    run_cmd += "--analytics_data_ttl %d " % (analytics_database_ttl)
                else:
                    #if nothing is provided we default to 168h
                    run_cmd += "--analytics_data_ttl 168 "
                print run_cmd
                run(run_cmd)
#end setup_collector

@task
@roles('database')
def setup_database():
    """Provisions database services in all nodes defined in database role."""
    execute("setup_database_node", env.host_string)

@task
def setup_database_node(*args):
    """Provisions database services in one or list of nodes. USAGE: fab setup_database_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        database_host = host_string
        database_host_password=env.passwords[host_string]
        tgt_ip = hstr_to_ip(get_control_host_string(database_host))
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run_cmd = "PASSWORD=%s python setup-vnc-database.py --self_ip %s " % (database_host_password, tgt_ip)
                database_dir = get_database_dir()
                if database_dir is not None:
                    run_cmd += "--data_dir %s " % (database_dir)
                run_cmd += "--seed_list %s" % (hstr_to_ip(get_control_host_string(env.roledefs['database'][0])))
                run(run_cmd)
#end setup_database
    
@task
@roles('webui')
def setup_webui():
    """Provisions webui services in all nodes defined in webui role."""
    execute("setup_webui_node", env.host_string)

@task
def setup_webui_node(*args):
    """Provisions webui services in one or list of nodes. USAGE: fab setup_webui_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        cfgm_host = get_control_host_string(env.roledefs['cfgm'][0])
        cfgm_ip = hstr_to_ip(cfgm_host)
        webui_host = get_control_host_string(host_string)
        cfgm_host_password=env.passwords[host_string]
        openstack_host = get_control_host_string(env.roledefs['openstack'][0])
        openstack_ip = hstr_to_ip(openstack_host)
        ncollectors = len(env.roledefs['collector'])
        database_host_list=[]
        for entry in env.roledefs['database']:
            database_host_list.append(get_control_host_string(entry))
        webui_host_list=[]
        for entry in env.roledefs['webui']:
            webui_host_list.append(get_control_host_string(entry))
        # Prefer local collector node
        if webui_host in env.roledefs['collector']:
            collector_ip = hstr_to_ip(webui_host)
        else:
            # Select based on index
            hindex = webui_host_list.index(webui_host)
            hindex = hindex % ncollectors
            collector_host = get_control_host_string(env.roledefs['collector'][hindex])
            collector_ip = hstr_to_ip(collector_host)
        cassandra_ip_list = [hstr_to_ip(cassandra_host) for cassandra_host in database_host_list]
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run("PASSWORD=%s python setup-vnc-webui.py --cfgm_ip %s --openstack_ip %s --collector_ip %s --cassandra_ip_list %s" %(cfgm_host_password, cfgm_ip, openstack_ip, collector_ip, ' '.join(cassandra_ip_list)))
#end setup_webui

@task
@roles('control')
def setup_control():
    """Provisions control services in all nodes defined in control role."""
    execute("setup_control_node", env.host_string)

@task
def setup_control_node(*args):
    """Provisions control services in one or list of nodes. USAGE: fab setup_control_node:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        cfgm_host = get_control_host_string(env.roledefs['cfgm'][0])
        cfgm_host_password=env.passwords[env.roledefs['cfgm'][0]]
        cfgm_ip = hstr_to_ip(cfgm_host)
        control_host = get_control_host_string(host_string)
        tgt_ip = hstr_to_ip(control_host)
        collector_host_list=[]
        for entry in env.roledefs['collector']:
            collector_host_list.append(get_control_host_string(entry))
        control_host_list=[]
        for entry in env.roledefs['control']:
            control_host_list.append(get_control_host_string(entry))
        # Prefer local collector node
        if control_host in collector_host_list:
            collector_ip = tgt_ip
        else:
            # Select based on index
            hindex = control_host_list.index(control_host)
            hindex = hindex % len(env.roledefs['collector'])
            collector_host = get_control_host_string(env.roledefs['collector'][hindex])
            collector_ip = hstr_to_ip(collector_host)
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                run("PASSWORD=%s python setup-vnc-control.py --self_ip %s --cfgm_ip %s --collector_ip %s" \
                     %(cfgm_host_password, tgt_ip, cfgm_ip, collector_ip))
                if detect_ostype() == 'centos':
                    run("PASSWORD=%s service contrail-control restart" % cfgm_host_password, pty=False)
#end setup_control

@task
@EXECUTE_TASK
@roles('openstack')
def setup_storage():
    """Provisions storage services."""
    execute("setup_storage_master", env.host_string)

@task
def setup_storage_master(*args):
    """Provisions storage services in one or list of nodes. USAGE: fab setup_storage:user@1.1.1.1,user@2.2.2.2"""
    for host_string in args:
        if host_string == env.roledefs['openstack'][0]:
            storage_host_entries=[]
            storage_pass_list=[]
            storage_host_list=[]
            storage_hostnames=[]
            for entry in env.roledefs['openstack']:
                for sthostname, sthostentry in zip(env.hostnames['all'], env.roledefs['all']):
                    if entry == sthostentry:
                        storage_hostnames.append(sthostname)
                        storage_host_password=env.passwords[entry]
                        storage_pass_list.append(storage_host_password)
                        storage_host = get_control_host_string(entry)
                        storage_data_ip=get_data_ip(storage_host, 'data')[0]
                        storage_host_list.append(storage_data_ip)
            for entry in env.roledefs['compute']:
                for sthostname, sthostentry in zip(env.hostnames['all'], env.roledefs['all']):
                    if entry == sthostentry and entry != env.roledefs['openstack'][0]:
                        storage_hostnames.append(sthostname)
                        storage_host_password=env.passwords[entry]
                        storage_pass_list.append(storage_host_password)
                        storage_host = get_control_host_string(entry)
                        storage_data_ip=get_data_ip(storage_host, 'data')[0]
                        storage_host_list.append(storage_data_ip)
            storage_master=get_control_host_string(env.roledefs['openstack'][0])
            storage_master_ip=get_data_ip(storage_master, 'data')[0]
            storage_master_password=env.passwords[env.roledefs['openstack'][0]]
            with  settings(host_string = storage_master, password = storage_master_password):
                with cd(INSTALLER_DIR):
	            cmd= "PASSWORD=%s python setup-vnc-storage.py --storage-master %s --storage-hostnames %s --storage-hosts %s --storage-host-tokens %s --storage-disk-config %s --storage-directory-config %s --live-migration %s" \
                            %(storage_master_password, storage_master_ip, ' '.join(storage_hostnames), ' '.join(storage_host_list), ' '.join(storage_pass_list), ' '.join(get_storage_disk_config()), ' '.join(get_storage_directory_config()), get_live_migration_opts())
                    print cmd
                    run(cmd)
#end setup_storage_master

@task
@EXECUTE_TASK
@roles('compute')
def setup_vrouter():
    """Provisions vrouter services in all nodes defined in vrouter role."""
    execute("setup_vrouter_node", env.host_string)

@task
def setup_vrouter_node(*args):
    """Provisions vrouter services in one or list of nodes. USAGE: fab setup_vrouter_node:user@1.1.1.1,user@2.2.2.2"""
    # make sure an agent pkg has been installed
    #try:
    #    run("yum list installed | grep contrail-agent")
    #except SystemExit as e:
    #    print "contrail-agent package not installed. Install it and then run setup_vrouter"
    #    return
    for host_string in args:
        ncontrols = len(env.roledefs['control'])
        cfgm_host = get_control_host_string(env.roledefs['cfgm'][0])
        cfgm_host_password=env.passwords[env.roledefs['cfgm'][0]]
        cfgm_ip = hstr_to_ip(cfgm_host)
        openstack_host = get_control_host_string(env.roledefs['openstack'][0])
        openstack_ip = hstr_to_ip(openstack_host)
        openstack_mgmt_ip = hstr_to_ip(env.roledefs['openstack'][0])
        compute_host = get_control_host_string(host_string)
        (tgt_ip, tgt_gw) = get_data_ip(host_string)
    
        # Try once from control section if present for mgmt,control=data scenario 
        if tgt_ip == host_string.split('@')[1]:
            (tgt_ip, tgt_gw) = get_data_ip(host_string,section='control')
      
        compute_mgmt_ip= host_string.split('@')[1]
        compute_control_ip= hstr_to_ip(compute_host)

        # Check and configure the VGW details
        set_vgw= 0
        if 'vgw' in env.roledefs:
            if host_string in env.roledefs['vgw']:
                set_vgw = 1
                public_subnet = env.vgw[host_string]['public_subnet'][0]
                public_vn_name = env.vgw[host_string]['public_vn_name'][0]
            
    
        with  settings(host_string=host_string):
            with cd(INSTALLER_DIR):
                cmd= "PASSWORD=%s python setup-vnc-vrouter.py --self_ip %s --cfgm_ip %s --openstack_ip %s --openstack_mgmt_ip %s --ncontrols %s %s" \
                         %(cfgm_host_password, compute_control_ip, cfgm_ip, openstack_ip, openstack_mgmt_ip, ncontrols, get_service_token())
                if tgt_ip != compute_mgmt_ip: 
                    cmd = cmd + " --non_mgmt_ip %s --non_mgmt_gw %s" %( tgt_ip, tgt_gw )
                if set_vgw:   
                    cmd = cmd + "--public_subnet %s --public_vn_name %s" %(public_subnet,public_vn_name)
                print cmd
                run(cmd)
#end setup_vrouter

@task
@roles('cfgm')
def prov_control_bgp():
    cfgm_ip = hstr_to_ip(get_control_host_string(env.roledefs['cfgm'][0]))

    control_host_list=[]
    for entry in env.roledefs['control']:
        control_host_list.append(get_control_host_string(entry))
    for control_host in env.roledefs['control']:
        with settings(host_string = control_host):
            tgt_ip = hstr_to_ip(get_control_host_string(control_host))
            tgt_hostname = run("hostname")

        with cd(UTILS_DIR):
            run("python provision_control.py --api_server_ip %s --api_server_port 8082 --host_name %s --host_ip %s --router_asn %s %s" \
                        %(cfgm_ip, tgt_hostname, tgt_ip, testbed.router_asn, get_mt_opts()))
#end prov_control_bgp

@task
@roles('cfgm')
def prov_external_bgp():
    cfgm_ip = hstr_to_ip(get_control_host_string(env.roledefs['cfgm'][0]))
    pre_cmd = ''

    for ext_bgp in testbed.ext_routers:
        ext_bgp_name = ext_bgp[0]
        ext_bgp_ip   = ext_bgp[1]
        with cd(UTILS_DIR):
            run("%s python provision_mx.py --api_server_ip %s --api_server_port 8082 --router_name %s --router_ip %s --router_asn %s %s" \
                        %(pre_cmd, cfgm_ip, ext_bgp_name, ext_bgp_ip, testbed.router_asn, get_mt_opts()))
#end prov_control_bgp

@roles('build')
@task
def setup_st():
    """Provisions required contrail services in all nodes as per the role definition.
    """
    execute(setup_storage)
#end setup_st

@roles('build')
@task
def setup_all():
    """Provisions required contrail services in all nodes as per the role definition.
    """
    execute(bash_autocomplete_systemd)
    execute(setup_database)
    execute(setup_openstack)
    execute(setup_cfgm)
    execute(setup_control)
    execute(setup_collector)
    execute(setup_webui)
    execute(setup_vrouter)
    execute(setup_storage)
    execute(prov_control_bgp)
    execute(prov_external_bgp)
    execute(compute_reboot)
#end setup_all

@roles('build')
@task
def setup_without_openstack():
    """Provisions required contrail packages in all nodes as per the role definition except the openstack.
       User has to provision the openstack node with their custom openstack pakckages.
    """
    execute(bash_autocomplete_systemd)
    execute(setup_database)
    execute(setup_cfgm)
    execute(setup_control)
    execute(setup_collector)
    execute(setup_webui)
    execute(setup_vrouter)
    execute(prov_control_bgp)
    execute(prov_external_bgp)
    execute(compute_reboot)

@roles('build')
@task
def reimage_and_setup_test():
    execute(all_reimage)
    sleep(900)
    execute(setup_all)
    sleep(300)
    execute(setup_test_env)
    
@roles('build')
@task
def setup_all_with_images():
    execute(bash_autocomplete_systemd)
    execute(setup_database)
    execute(setup_openstack)
    execute(setup_cfgm)
    execute(setup_control)
    execute(setup_collector)
    execute(setup_webui)
    execute(setup_vrouter)
    execute(prov_control_bgp)
    execute(prov_external_bgp)
    execute(add_images)
    execute(compute_reboot)

@roles('build')
@task
def run_setup_demo():
    execute(bash_autocomplete_systemd)
    execute(setup_database)
    execute(setup_openstack)
    execute(setup_cfgm)
    execute(setup_control)
    execute(setup_collector)
    execute(setup_webui)
    execute(setup_vrouter)
    execute(prov_control_bgp)
    execute(prov_external_bgp)
    execute(config_demo)
    execute(add_images)
    execute(compute_reboot)
#end run_setup_demo

@task
def setup_interface(intf_type = 'both'):
    '''
    Configure the IP address and netmask for non-mgmt interface based on parameter passed in non_mgmt stanza of testbed file. Also generate ifcfg file for the interface if the file is not present. 
    '''

    if intf_type == 'both':
        intf_type_list = ['control', 'data']
    else:
        intf_type_list = intf_type

    for intf_type in intf_type_list:
        tgt_ip = None
        tgt_gw= None
        setup_info={}
        if intf_type == 'control' :
            setup_info = getattr(testbed, 'control', None)
        else :
            setup_info = getattr(testbed, 'data', None)
        if setup_info:
            for host_str in setup_info.keys():
               isBond=0
               if 'device' in setup_info[host_str].keys(): 
                   tgt_device = setup_info[host_str]['device']
                   tgt_ip = str(IPNetwork(setup_info[host_str]['ip']).ip)
                   tgt_netmask = str(IPNetwork(setup_info[host_str]['ip']).netmask)
                   tgt_gw = setup_info[host_str]['gw']
                   with settings(host_string = host_str):
                       with settings(warn_only = True):
                           count1=run("ifconfig -a | grep -c %s" %(tgt_device))
                       # Even if intreface is not present, check if intreface is bond
                       if 'bond' in tgt_device:
                           isBond=1
                           count1=1
                       if int(count1):
                           if not isBond:
                               with settings(warn_only = True):
                                   count2=run("ifconfig %s | grep -c %s" %(tgt_device,tgt_ip))
                           else:
                               count2=0
                           if not int(count2):
                               if not isBond:
                                   # Device is present and IP is not present. Creating the required ifcfg file
                                   hwaddr = run("ifconfig %s | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'" %(tgt_device))
                               filename = '/etc/sysconfig/network-scripts/' +  'ifcfg-' + tgt_device
                               bkp_file_name= filename+ '_bkp'
                               if 'bond' in tgt_device:
                                   create_bond(tgt_host=host_str,bond_ip=setup_info[host_str]['ip'])
                               else:
                                   with settings(warn_only = True):
                                       run("cp %s  %s" %(filename,bkp_file_name))
                                   run("rm -rf %s" %(filename))
                                   run("echo DEVICE=%s >> %s" %(tgt_device,filename))
                                   run("echo ONBOOT=yes >> %s" %(filename))
                                   run("echo NM_CONTROLLED=no >>  %s" %(filename))
                                   run("echo BOOTPROTO=none >>  %s" %(filename))
                                   run("echo NETMASK=%s >>  %s" %(tgt_netmask,filename))
                                   run("echo IPADDR=%s >>  %s" %(tgt_ip,filename))
                                   run("echo HWADDR=%s >>  %s" %(hwaddr,filename))
                               restart_network_service(host_str)

@task
def create_bond(tgt_host=None,bond_ip=None):
    '''
    Crete the bond interface based on the parameter passed in bond stanza of testbed file
    '''
    bond_info = getattr(testbed, 'bond', None)
    if bond_info:
        tgt_host_list=None
        if tgt_host == None:
            tgt_host_list=bond_info.keys()
        else:
            tgt_host_list=[tgt_host]
        for tgt_host in tgt_host_list:
            member=bond_info[tgt_host]['member']
            name=bond_info[tgt_host]['name']
            mode=bond_info[tgt_host]['mode']
            create_intf_file(tgt_host,name,member,mode,bond_ip)
            restart_network_service(tgt_host)

@roles('build')
@task
def reset_config():
    '''
    Reset api-server and openstack config and run the setup-scripts again incase you get into issues
    '''
    try:
        execute(api_server_reset, 'add', role='cfgm')
        execute(cleanup_os_config)
        execute(setup_database)
        execute(setup_openstack)
        execute(setup_cfgm)
        execute(setup_control)
        execute(setup_collector)
        execute(setup_webui)
        execute(setup_vrouter)
        execute(prov_control_bgp)
        execute(prov_external_bgp)
        sleep(5)
    except SystemExit:
        execute(api_server_reset, 'delete', role='cfgm')
        raise SystemExit("\nReset config Failed.... Aborting")
    else:
        execute(api_server_reset, 'delete', role='cfgm')
    execute(all_reboot)
#end reset_config
