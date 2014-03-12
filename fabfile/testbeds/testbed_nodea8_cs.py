from fabric.api import env

hypervisor_type = 'XenServer'
controller_type = 'Cloudstack'

controller = 'root@10.204.216.252'
xenserver = 'root@10.204.216.60'
builder = 'vjoshi@10.204.216.56'

# Password used while loging into all hosts
env.password = 'c0ntrail123'

env.hosts = [
    controller,
    xenserver,
    builder
]

env.passwords = {
    controller: 'c0ntrail123',
    xenserver: 'c0ntrail123',
    builder: 'secret',
}

env.roledefs = {
    'control': [controller],
    'compute': [xenserver],
# database is needed so that fab setup_test_env doesn't break
    'database': [controller],
    'collector': [controller],
    'build': [builder],
    'cfgm': [controller],
    'all' : [ controller, xenserver ],
}

env.hostnames = {
    'all': ['nodea8-cs','nodec3']
}

# Cloudstack specific config
config = {
    # Repos, NFS, etc.
    'nfs_share_path': '10.204.216.49:/cs-attic',
    'yum_repo_host': '10.204.216.51',
    'cobbler_server_ip': '10.204.216.51',
    'vm_template_url': 'http://10.204.216.51/cloudstack/vm_templates/centos56-x86_64-xen.vhd.bz2',
    'vm_template_name': 'CentOS',
    'vsrx_template_url': 'http://10.204.216.51/cloudstack/vm_templates/juniper-vsrx-firefly-template.vhd.bz2',
    'vsrx_template_name': 'Juniper vSRX',
    'mx_ip' : '10.204.216.253',
    'route_target' : '10003',

    # Cloud configuration
    'cloud': {
        'username': 'admin',
        'password': 'password',

        'external_dns': '8.8.8.8',
        'internal_dns': '10.204.208.221',

        'pods': {
            'a6': {
                'startip': '10.204.216.230',
                'endip'  : '10.204.216.240',
                'gateway': '10.204.216.254',
                'netmask': '255.255.255.0',

                'clusters': {
                    'a6-xen1': {
                        'hypervisor_type': 'XenServer',

                        'hosts': {
                            'xen1': '10.204.216.60'
                        }
                    }
                }
            }
        },

        'public_net': {
            'startip': '10.204.219.100',
            'endip': '10.204.219.110',
            'gateway': '10.204.219.254',
            'netmask': '255.255.255.0'
        }
    }
}
env.config = config

env.test_repo_dir='/homes/vjoshi/cs/test'
env.mail_to='vjoshi@juniper.net'


