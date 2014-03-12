import os
from netaddr import *

from fabric.api import *

from fabfile.config import testbed
from fabfile.utils.host import *

def get_storage_disk_config():
    storage_info = getattr(testbed, 'storage_node_config', None)
    storage_disk_node_list=[]
    if storage_info:
        for entry in storage_info.keys():
            storage_host = get_control_host_string(entry)
            for sthostname, sthostentry in zip(env.hostnames['all'], env.roledefs['all']):
                if entry == sthostentry:
                    if 'disks' in storage_info[entry].keys():
                        for disk_entry in storage_info[entry]['disks']:
                            storage_disk_node = sthostname + ':' + disk_entry
                            storage_disk_node_list.append(storage_disk_node)
    if storage_disk_node_list == []:
        storage_disk_node_list.append('none')
    return (storage_disk_node_list)
#end get_storage_disk_config

def get_storage_directory_config():
    storage_info = getattr(testbed, 'storage_node_config', None)
    storage_directory_node_list=[]
    if storage_info:
        for entry in storage_info.keys():
            storage_host = get_control_host_string(entry)
            for sthostname, sthostentry in zip(env.hostnames['all'], env.roledefs['all']):
                if entry == sthostentry:
                    if 'directories' in storage_info[entry].keys():
                        for directory_entry in storage_info[entry]['directories']:
                            storage_directory_node = sthostname + ':' + directory_entry
                            storage_directory_node_list.append(storage_directory_node)
    if storage_directory_node_list == []:
        storage_directory_node_list.append('none')
    return (storage_directory_node_list)
#end get_storage_directory_config

