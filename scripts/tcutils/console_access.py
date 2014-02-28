#------------------------
#To be able to talk to Guest VMs on xen server
#Usage: python console-access.py i-1-9-VM root c0ntrail123 "ls -l" "ls -l /tmp"
#------------------------
import pexpect
import time
import sys
import subprocess

def _cmd(cmd):
    proc=subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output,err)=proc.communicate()
    return(output,err)
#end _cmd

def get_domain_id( vm_internal_name) :

    vm_id= _cmd('xe vm-list name-label=%s | grep uuid  | awk \'{ print $5 } \'' %(vm_internal_name) )[0].strip('\n')
    vm_dom_id= _cmd('xe vm-param-get uuid=%s param-name=dom-id' %(vm_id) )[0].strip('\n')
    return vm_dom_id
#end get_domain_id

def run_vm_cmd_on_xen_locally( name, username, password, cmd ):
    outputs=[]
    vm_internal_name= name

    vm_dom_id= get_domain_id( vm_internal_name )
    a= pexpect.spawn('/usr/lib/xen/bin/xenconsole %s' %(vm_dom_id) , maxread=10000, timeout=60)
    a.sendline('')
    try:
        prompt_str= '[%#] $'
        i = a.expect (['[%#] $','login: $' ])
        if i== 1:
            a.sendline( username )
            a.expect('assword:')
            a.sendline(password)
            a.expect(prompt_str)
        a.sendline(cmd)
        a.expect(prompt_str)
        op= a.before.replace('\r','')
        output= '\n'.join(op.split('\n')[1:-1])
        a.sendcontrol(']')
        print output
    except pexpect.TIMEOUT,e:
        print a.before, a.after
        print 'Timeout while waiting for prompt..'
        output = None
    return output
#end run_vm_cmd_on_xen_locally

if __name__ == "__main__":
    run_vm_cmd_on_xen_locally( sys.argv[1], sys.argv[2], sys.argv[3] , sys.argv[4] )
