import os
import re

from fabfile.config import *
from fabfile.templates import compute_ovf_template

def _get_var(var, default=None):
    try:
        return var
    except Exception:
        return default
#end _get_var

def configure_esxi_network(compute_vm_info):
    #ESXI Host Login
    host_string = '%s@%s' %(compute_vm_info['esxi']['username'],
                           compute_vm_info['esxi']['ip'])
    password = _get_var(compute_vm_info['esxi']['password'])
    
    compute_pg = _get_var(compute_vm_info['port_group'],'compute_pg')
    fabric_pg = _get_var(compute_vm_info['esxi']['vm_port_group'],'fabric_pg')
    vswitch0 = _get_var(compute_vm_info['esxi']['vswitch'],'vSwitch0')
    vswitch1 = _get_var(compute_vm_info['vswitch'],'vSwitch1')
    uplink_nic = compute_vm_info['esxi']['uplink_nic']
    with settings(host_string = host_string, password = password, 
                    warn_only = True, shell = '/bin/sh -l -c'):
        run('esxcli network vswitch standard add --vswitch-name=%s' %(
                vswitch1))
        run('esxcli network vswitch standard portgroup add --portgroup-name=%s --vswitch-name=%s' %(compute_pg, vswitch1))
        run('esxcli network vswitch standard portgroup add --portgroup-name=%s --vswitch-name=%s' %(fabric_pg, vswitch0))
        run('esxcli network vswitch standard uplink add --uplink-name=%s --vswitch-name=%s' %(uplink_nic, vswitch0))

@task
def create_ovf(compute_vm_info):
    compute_vm_name = _get_var(_compute_vm_info['vm_name'],'Fedora-Compute-VM')
    compute_vm_vmdk = compute_vm_info['vmdk']
#    compute_vm_vmdk = 'Fedora-Compute-VM1-disk1.vmdk'
    compute_pg = _get_var(compute_vm_info['port_group'],'compute_pg')
    fabric_pg = _get_var(compute_vm_info['esxi']['vm_port_group'],'fabric_pg')
    ovf_file = '%s.ovf' %(compute_vm_name)
    template_vals = {'__compute_vm_name__': compute_vm_name,
                     '__compute_vm_vmdk__': compute_vm_vmdk,
                     '__compute_pg__': compute_pg,
                     '__fabric_pg__': fabric_pg,
                    }
    _template_substitute_write(compute_ovf_template.template,
                               template_vals, ovf_file)
    ovf_file_path = os.path.realpath(ovf_file)
    print "\n\nOVF File %s created for VM %s" %(ovf_file_path, compute_vm_name)
#end create_ovf
    

def _template_substitute(template, vals):
    data = template.safe_substitute(vals)
    return data
#end _template_substitute

def _template_substitute_write(template, vals, filename):
    data = _template_substitute(template, vals)
    outfile = open(filename, 'w')
    outfile.write(data)
    outfile.close()
#end _template_substitute_write
