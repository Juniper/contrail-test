from fabfile.config import *

def copy_pkg(tgt_host, pkg_file):
    with settings(host_string = tgt_host):
        put(pkg_file)
#end _copy_pkg

def install_pkg(tgt_host, pkg_file):
    with settings(host_string = tgt_host):
        run("rpm -iv --force %s" %(pkg_file.split('/')[-1]))
#end _install_pkg

def detect_ostype():
    output = run('uname -a')
    dist = 'centos'
    if 'el6' in output:
        dist = 'centos'
    elif 'fc17' in output:
        dist = 'fedora'
    elif 'xen' in output:
        dist = 'xen'
    return dist
#end detect_ostype
