from fabric.api import local
from fabric.api import settings, run
from tcutils.test_lib.test_utils import assertEqual
import os
import time
from base import ServerManagerTest
import test
import fixtures
from smgr_common import SmgrFixture
import json
import pdb


def inventory_show_tests(self):
    cluster_id=self.smgr_fixture.get_cluster_id()
    cmd="server-manager show server --cluster_id " + cluster_id + " --select 'id' | grep 'id' | head -n 1 | cut -d ':' -f 2  | cut -d '"
    cmd=cmd + '"' + "' -f 2"
    server_id=local(cmd,capture=True)

    #Show and check if server inventory has the desired fields.
    cmd="server-manager show inventory --server_id " + server_id
    server_inventory=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_inventory) and
        ('"cluster_id": "'+cluster_id+'"' in server_inventory) and
        ('interface_infos' in server_inventory) and
        ('fru_infos' in server_inventory) and
        ('cpu_info_state' in server_inventory) and
        ('mem_state' in server_inventory) and
        ('kernel_version' in server_inventory)):
        self.logger.info("Verification of show inventory for server with server_id Passed.")
    else:
        self.logger.error("Verification of show inventory for server with server_id Failed.")
        return False

    #Show and check if server inventory has the desired fields when displayed with cluster_id.
    cmd="server-manager show inventory --cluster_id " + cluster_id
    server_inventory=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_inventory) and
        ('"cluster_id": "'+cluster_id+'"' in server_inventory) and
        ('interface_infos' in server_inventory) and
        ('fru_infos' in server_inventory) and
        ('cpu_info_state' in server_inventory) and
        ('mem_state' in server_inventory) and
        ('kernel_version' in server_inventory)):
        self.logger.info("Verification of show inventory for server with cluster_id Passed.")
    else:
        self.logger.error("Verification of show inventory for server with cluster_id Failed.")
        return False

    #Show and check if server inventory has the desired fields when displayed with tags.
    server_ip=self.smgr_fixture.get_ip_using_server_id(server_id)
    self.smgr_fixture.add_tag_to_server(server_ip,"datacenter","inventory_tag")
    cmd='server-manager show inventory --tag "datacenter=inventory_tag"'
    server_inventory=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_inventory) and
        ('"cluster_id": "'+cluster_id+'"' in server_inventory) and
        ('interface_infos' in server_inventory) and
        ('fru_infos' in server_inventory) and
        ('cpu_info_state' in server_inventory) and
        ('mem_state' in server_inventory) and
        ('kernel_version' in server_inventory)):
        self.logger.info("Verification of show inventory with tags Passed.")
    else:
        self.logger.error("Verification of show inventory with tags Failed.")
        return False
    return True
#end inventory_show_tests

def inventory_tests(self, node_name=None):
    if node_name is None:
        self.logger.error("ERROR :: Target node name has to be specified to test inventory information.")
        return False
    self.logger.info("------------INVENTORY TEST FOR NODE %s------------" % node_name)
    local("server-manager-client display inventory --server_id %s > working_db.txt" % node_name)
    fd=open('working_db.txt','r')
    lines=fd.readlines()
    fd.close()
    fd=open('working_db.json','w')
    for i in range(1,len(lines)-1):
        fd.write(lines[i])
    fd.close()
    fd=open('working_db.json','r')
    inventory_data=json.load(fd)
    fd.close()

    node_ip=self.smgr_fixture.get_ip_using_server_id(node_name)
    node_pswd=self.smgr_fixture.get_pswd_using_server_id(node_name)

    #Check for cpu details in inventory.
    with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
        cpu_cores=run('cat /proc/cpuinfo | grep "cpu cores" | head -n 1 |cut -d ":" -f2')
        clock_speed=run('cat /proc/cpuinfo | grep "cpu MHz" | head -n 1 |cut -d ":" -f2')
        model=run('cat /proc/cpuinfo | grep "model name" | head -n 1 |cut -d ":" -f2')

    assertEqual(int(cpu_cores), inventory_data['ServerInventoryInfo']['cpu_cores_count'],
        "cpu_cores_count mismatch for node %s = inventory_data - %s, proc-cpuinfo data - %s" % (node_name,inventory_data['ServerInventoryInfo']['cpu_cores_count'],cpu_cores))
    assertEqual(float(clock_speed), float(inventory_data['ServerInventoryInfo']['cpu_info_state']['clock_speed_MHz']),
        "clock_speed mismatch for node %s = inventory_data - %s, proc-cpuinfo data - %s"
            % (node_name,float(inventory_data['ServerInventoryInfo']['cpu_info_state']['clock_speed_MHz']),float(clock_speed)))
    assertEqual(model, inventory_data['ServerInventoryInfo']['cpu_info_state']['model'],
        "model mismatch for node %s = inventory_data - %s, proc-cpuinfo data - %s"
            % (node_name,inventory_data['ServerInventoryInfo']['cpu_info_state']['model'],model))

    #Check for interface details in inventory both physical and virtual intrerfaces should be listed.
    with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
        intf_names=run("ifconfig -a | grep 'Link encap' | awk '{print $1}'")
        intf_list=intf_names.split('\r\n')

    track_intf=list(intf_list)
    for i in range(0,len(track_intf)):
        if '-' in track_intf[i]:
            del track_intf[i]

    for intf_data in inventory_data['ServerInventoryInfo']['interface_infos']:
        if '_' in intf_data['interface_name']:
            continue
        if intf_data['interface_name'] in track_intf:
            if (intf_data['ip_addr'] and intf_data['ip_addr'] != 'N/A'):
                with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
                    ip_addr=run("ifconfig " + intf_data['interface_name'] + " | grep inet | awk '{print $2}' | cut -d ':' -f 2")
                assertEqual(ip_addr, intf_data['ip_addr'], "ip address mis-match for interface %s on node %s. inventory data - %s, ifconfig data %s"
                    % (intf_data['interface_name'],node_name,intf_data['ip_addr'],ip_addr))

            if (intf_data['macaddress'] and intf_data['macaddress'] != 'N/A'):
                with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
                    mac_addr=run("cat /sys/class/net/" + intf_data['interface_name'] + "/address")
                assertEqual(mac_addr.lower(), intf_data['macaddress'].lower(), "mac address mis-match for interface %s on node %s. inventory data - %s, ifconfig data %s"
                    % (intf_data['interface_name'],node_name,intf_data['macaddress'].lower(),mac_addr.lower()))

            if (intf_data['netmask'] and intf_data['netmask'] != 'N/A'):
                with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
                    mask=run("ifconfig " + intf_data['interface_name'] + " | grep Mask | awk '{print $4}' | cut -d ':' -f 2")
                assertEqual(mask, intf_data['netmask'], "netmask mis-match for interface %s on node %s. inventory data - %s, ifconfig data %s"
                    % (intf_data['interface_name'],node_name,intf_data['netmask'],mask))

        else:
            self.logger.error("ERROR :: Interface not found in inventory but there as part of the system info")
            self.logger.error("ERROR :: Inventory interface information %s" % intf_data)
            self.logger.error("ERROR :: System interface information %s" % track_intf)
            return False

    #Check for memory state and number of disks.
    with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
        dimm_size_mb=run("dmidecode -t 17 | grep Size | head -n 1 | awk '{print $2}'")
        mem_speed_MHz=run("dmidecode -t 17 | grep Speed | head -n 1 | awk '{print $2}'")
        mem_type=run("dmidecode -t 17 | grep Type | head -n 1 | awk '{print $2}'")
        num_of_dimms=run("dmidecode -t 17 | grep 'Memory Device' | wc -l")
        swap_size_mb=run("vmstat -s -S M | grep 'total swap' | awk '{print $1}'")
        total_mem_mb=run("vmstat -s -S M | grep 'total memory' | awk '{print $1}'")

    assertEqual(int(dimm_size_mb), inventory_data['ServerInventoryInfo']['mem_state']['dimm_size_mb'],
        "dimm_size_mb mismatch for node %s = inventory_data - %s, dmidecode data - %s" % (node_name,inventory_data['ServerInventoryInfo']['mem_state']['dimm_size_mb'],int(dimm_size_mb)))
    assertEqual(int(mem_speed_MHz), inventory_data['ServerInventoryInfo']['mem_state']['mem_speed_MHz'],
        "mem_speed_MHz mismatch for node %s = inventory_data - %s, dmidecode data - %s" % (node_name,inventory_data['ServerInventoryInfo']['mem_state']['mem_speed_MHz'],int(mem_speed_MHz)))
    assertEqual(mem_type, inventory_data['ServerInventoryInfo']['mem_state']['mem_type'],
        "mem_type mismatch for node %s = inventory_data - %s, dmidecode data - %s" % (node_name,inventory_data['ServerInventoryInfo']['mem_state']['mem_type'],mem_type))
    assertEqual(int(num_of_dimms), inventory_data['ServerInventoryInfo']['mem_state']['num_of_dimms'],
        "num_of_dimms mismatch for node %s = inventory_data - %s, dmidecode data - %s" % (node_name,inventory_data['ServerInventoryInfo']['mem_state']['num_of_dimms'],int(num_of_dimms)))

    if (float(swap_size_mb)*0.98 <= float(inventory_data['ServerInventoryInfo']['mem_state']['swap_size_mb']) <= float(swap_size_mb)*1.02):
        self.logger.info("swap_size_mb matched inventory data.")
    else:
        self.logger.error("swap_size_mb for node %s = inventory_data - %s, vmstat data - %s --- Not in range 98% to 102%"
            % (node_name,float(inventory_data['ServerInventoryInfo']['mem_state']['swap_size_mb']),float(swap_size_mb)))
        return False

    if (float(total_mem_mb)*0.98 <= float(inventory_data['ServerInventoryInfo']['mem_state']['total_mem_mb']) <= float(total_mem_mb)*1.02):
        self.logger.info("total_mem_mb matched inventory data.")
    else:
        self.logger.error("total_mem_mb for node %s = inventory_data - %s, vmstat data - %s --- Not in range 98% to 102%"
            % (node_name,float(inventory_data['ServerInventoryInfo']['mem_state']['total_mem_mb']),float(total_mem_mb)))
        return False

    #Check for system related inventory information.
    with settings(host_string='root@'+node_ip, password=node_pswd, warn_only=True):
        board_manufacturer=run("dmidecode -t 3 | grep 'Manufacturer' | awk '{print $2}'")
        kernel_version=run("uname -r | cut -d '-' -f 1")
        name=run("uname -n")
        hardware_model=run("uname -i")
        node_os=run("uname -v | cut -d '-' -f 2 | awk '{print $1}'")

    assertEqual(board_manufacturer, inventory_data['ServerInventoryInfo']['fru_infos'][0]['board_manufacturer'],
        "board_manufacturer mismatch for node %s = inventory_data - %s, dmidecode data - %s"
            % (node_name,inventory_data['ServerInventoryInfo']['fru_infos'][0]['board_manufacturer'],board_manufacturer))
    assertEqual(kernel_version, inventory_data['ServerInventoryInfo']['kernel_version'],
        "kernel_version mismatch for node %s = inventory_data - %s, uname data - %s" % (node_name,inventory_data['ServerInventoryInfo']['kernel_version'],kernel_version))
    assertEqual(name, inventory_data['ServerInventoryInfo']['name'],
        "name mismatch for node %s = inventory_data - %s, uname data - %s" % (node_name,inventory_data['ServerInventoryInfo']['name'],name))
    assertEqual(hardware_model, inventory_data['ServerInventoryInfo']['hardware_model'],
        "hardware_model mismatch for node %s = inventory_data - %s, uname data - %s" % (node_name,inventory_data['ServerInventoryInfo']['hardware_model'],hardware_model))
    assertEqual(node_os, inventory_data['ServerInventoryInfo']['os'],
        "os mismatch for node %s = inventory_data - %s, uname data - %s" % (node_name,inventory_data['ServerInventoryInfo']['os'],node_os))

    os.remove('working_db.txt')
    self.logger.info("------------END OF INVENTORY TEST FOR NODE %s------------" % node_name)
    return True
#end inventory_tests

def monitoring_show_tests(self):
    cluster_id=self.smgr_fixture.get_cluster_id()
    cmd="server-manager-client display server --json --cluster_id " + cluster_id + " --select 'id' | grep 'id' | head -n 1 | cut -d ':' -f 2  | cut -d '"
    cmd=cmd + '"' + "' -f 2"
    server_id=local(cmd,capture=True)

    #Show and check if server monitoring has the desired fields.
    cmd="server-manager-client display monitoring --server_id " + server_id
    server_monitoring=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_monitoring) and
        ('"cluster_id": "'+cluster_id+'"' in server_monitoring) and
        ('chassis_state' in server_monitoring) and
        ('disk_usage_stats' in server_monitoring) and
        ('disk_usage_totals' in server_monitoring) and
        ('file_system_view_stats' in server_monitoring) and
        ('network_info_stats' in server_monitoring) and
        ('network_info_totals' in server_monitoring) and
        ('resource_info_stats' in server_monitoring) and
        ('sensor_stats' in server_monitoring)):
        self.logger.info("Verification of show monitoring for server with server_id Passed.")
    else:
        self.logger.error("Verification of show monitoring for server with server_id Failed.")
        return False

    #Show and check if server monitoring has the desired fields when displayed with cluster_id.
    cmd="server-manager-client display monitoring --cluster_id " + cluster_id
    server_monitoring=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_monitoring) and
        ('"cluster_id": "'+cluster_id+'"' in server_monitoring) and
        ('chassis_state' in server_monitoring) and
        ('disk_usage_stats' in server_monitoring) and
        ('disk_usage_totals' in server_monitoring) and
        ('file_system_view_stats' in server_monitoring) and
        ('network_info_stats' in server_monitoring) and
        ('network_info_totals' in server_monitoring) and
        ('resource_info_stats' in server_monitoring) and
        ('sensor_stats' in server_monitoring)):
        self.logger.info("Verification of show monitoring for server with cluster_id Passed.")
    else:
        self.logger.error("Verification of show monitoring for server with cluster_id Failed.")
        return False

    #Show and check if server monitoring has the desired fields when displayed with tags.
    server_ip=self.smgr_fixture.get_ip_using_server_id(server_id)
    self.smgr_fixture.add_tag_to_server(server_ip,"datacenter","monitoring_tag")
    cmd='server-manager-client display monitoring --tag "datacenter=monitoring_tag"'
    server_monitoring=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_monitoring) and
        ('"cluster_id": "'+cluster_id+'"' in server_monitoring) and
        ('chassis_state' in server_monitoring) and
        ('disk_usage_stats' in server_monitoring) and
        ('disk_usage_totals' in server_monitoring) and
        ('file_system_view_stats' in server_monitoring) and
        ('network_info_stats' in server_monitoring) and
        ('network_info_totals' in server_monitoring) and
        ('resource_info_stats' in server_monitoring) and
        ('sensor_stats' in server_monitoring)):
        self.logger.info("Verification of show monitoring with tags Passed.")
    else:
        self.logger.error("Verification of show monitoring with tags Failed.")
        return False
    return True

#end monitoring_show_tests

def monitoring_functionality_tests(self):
    cluster_id=self.smgr_fixture.get_cluster_id()
    cmd="server-manager show server --cluster_id " + cluster_id + " --select 'id' | grep 'id' | head -n 1 | cut -d ':' -f 2  | cut -d '"
    cmd=cmd + '"' + "' -f 2"
    server_id=local(cmd,capture=True)

    #Check and verify if monitoring data is available.
    cmd='server-manager-client display monitoring'
    server_monitoring=local(cmd,capture=True)
    if (('"name": "'+server_id+'"' in server_monitoring) and
        ('"cluster_id": "'+cluster_id+'"' in server_monitoring) and
        ('chassis_state' in server_monitoring) and
        ('disk_usage_stats' in server_monitoring) and
        ('disk_usage_totals' in server_monitoring) and
        ('file_system_view_stats' in server_monitoring) and
        ('network_info_stats' in server_monitoring) and
        ('network_info_totals' in server_monitoring) and
        ('resource_info_stats' in server_monitoring) and
        ('sensor_stats' in server_monitoring)):
        self.logger.info("Verification of show monitoring Passed.")

        #Disable the monitoring plugin and restart SM to stop monitoring.
        cmd='sed -i s/monitoring_plugin/#monitoring_plugin/ /opt/contrail/server_manager/sm-config.ini'
        local(cmd)
        cmd='service contrail-server-manager restart'
        local(cmd)
        time.sleep(10)
        cmd='service contrail-server-manager status'
        SM_status=local(cmd,capture=True)
        if 'not running' in SM_status:
            self.logger.error('ERROR :: Failed to restart Server Manager after disabling monitoring plugin.')
            return False

        #Check that no monitoring data is available once the plugin is disabled.
        #Check that right message is passed on to the user about enabling monitoring.
        cmd='server-manager-client display monitoring'
        server_monitoring=local(cmd,capture=True)
        if (not('"return_code": 9' in server_monitoring) or
            (not('Reset the configuration correctly and restart Server Manager.' in server_monitoring))):
            self.logger.error('ERROR :: Failed to stop monitoring plugin by commenting it out in sm-config.ini file'+
                               ' and restarting Server Manager process')
            return False

        #Re-enable monitoring plugin and check the monitoring data.
        cmd='sed -i s/#monitoring_plugin/monitoring_plugin/ /opt/contrail/server_manager/sm-config.ini'
        local(cmd)
        cmd='service contrail-server-manager restart'
        local(cmd)
        time.sleep(10)
        cmd='service contrail-server-manager status'
        SM_status=local(cmd,capture=True)
        if 'not running' in SM_status:
            self.logger.error('ERROR :: Failed to restart Server Manager after enabling monitoring plugin.')
            return False

        #Sleep for monitoring timer interval.
        sleep_time=local("cat /opt/contrail/server_manager/sm-config.ini | grep monitoring_frequency | awk '{print $3}'", capture=True)
        time.sleep(int(sleep_time)+5)
        cmd='server-manager-client display monitoring'
        server_monitoring=local(cmd,capture=True)
        if (('"name": "'+server_id+'"' in server_monitoring) and
            ('"cluster_id": "'+cluster_id+'"' in server_monitoring) and
            ('chassis_state' in server_monitoring) and
            ('disk_usage_stats' in server_monitoring) and
            ('disk_usage_totals' in server_monitoring) and
            ('file_system_view_stats' in server_monitoring) and
            ('network_info_stats' in server_monitoring) and
            ('network_info_totals' in server_monitoring) and
            ('resource_info_stats' in server_monitoring) and
            ('sensor_stats' in server_monitoring)):
            self.logger.info("Verification of show monitoring after re-enabling the plugin Passed.")
        else:
            self.logger.error("Verification of show monitoring after re-enabling the plugin Failed.")
            return False
    else:
        self.logger.error("Verification of show monitoring Failed.")
        return False
    return True

#end monitoring_functionality_tests
