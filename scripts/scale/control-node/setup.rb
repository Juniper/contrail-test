#!/usr/bin/env ruby

require 'pp'

@cluster = "10.84.26.23"
@user = ENV["USER"]

def sh (cmd, ignore = false)
    puts cmd
    output = `#{cmd}`
    exit -1 if !ignore and $?.to_i != 0
    puts output
    return output
end

def rsh (ip, cmds, ignore = false)
    cmds.each { |cmd|
        sh(%{sshpass -p c0ntrail123 ssh -q root@#{ip} "#{cmd}"}, ignore)
    }
end

def csh (cmds, ignore = false)
    cmds.each { |cmd| rsh(@cluster, cmds, ignore) }
end

def rcp (ip, src, dst = ".", ignore = false)
    sh("sshpass -p c0ntrail123 scp -q #{src} root@#{ip}:#{dst}", ignore)
end

def junos_setup
    csh("glance image-create --container-format bare --disk-format raw --progress --file bgp-scale-vsrx.img --name bgp-scale-vsrx --is-public True")
end

def create_nodes_in_cluster
    csh([%{/root/CI_ADMIN/ci-openstack.sh nova list | \grep #{@user} | \grep bgp-scale | awk '{print $2}' | xargs /root/CI_ADMIN/ci-openstack.sh nova delete}], true
    )
    cmn = "launch_vms.rb --second-nic bgp_scale_l2 --flavor m1.xlarge"
    cmds = <<EOF
#{cmn} -j -n #{@user}-bgp-scale-node-vsrx1 1
#{cmn} -j -n #{@user}-bgp-scale-node-vsrx2 1
#{cmn} -u -n #{@user}-bgp-scale-node-config1 1
#{cmn} -u -n #{@user}-bgp-scale-node-control1 1
#{cmn} -u -n #{@user}-bgp-scale-node-control2 1
#{cmn} -u -n #{@user}-bgp-scale-node-testserver1 1
#{cmn} -u -n #{@user}-bgp-scale-node-testserver2 1
EOF
    cmds.split(/\n/).each { |cmd| Process.fork { csh([cmd]) } }
    Process.waitall
end

def load_nodes_from_cluster
    find_nodes = <<EOF
sshpass -p c0ntrail123 ssh -q root@10.84.26.23 CI_ADMIN/ci-openstack.sh nova list | \grep bgp-scale
EOF

    @nodes = { }
        sh(find_nodes).split(/\n/).each { |node|
        next if node !~ /bgp-scale-node-(.*?)-(\d+)-(\d+)-(\d+)-(\d+).*internet=(\d+)\.(\d+)\.(\d+)\.(\d+)/
        type = $1
        public_ip = "#{$2}.#{$3}.#{$4}.#{$5}"
        private_ip = "#{$6}.#{$7}.#{$8}.#{$9}"
        secondary_ip = "1.1.1.#{$9}"
        node = $1 if node =~ /\s+(#{ENV['USER']}-bgp-scale-node-.*?)\s+/
        @nodes[type] = {
            :host => node, :private_ip => private_ip, :public_ip => public_ip,
            :secondary_ip => secondary_ip
        }
    }
    pp @nodes
end

def configure_secondary_ips
    @nodes.each { |type, node|
        next if type =~ /vsrx/
        rsh(node[:public_ip], "ifconfig eth1 up")
        rsh(node[:public_ip], "ip addr add #{node[:secondary_ip]}/24 dev eth1")
    }
end

def fix_nodes
    @nodes.each { |type, node|
        next if type =~ /vsrx/
        cmds = <<EOF
apt-get -y remove python-iso8601
apt-get -y autoremove
EOF
        Process.fork { rsh(node[:public_ip], cmds.split(/\n/)) }
    }
    Process.waitall
end

def setup_topo
    topo = <<EOF
from fabric.api import env

host1 = 'root@#{@nodes["config1"][:private_ip]}'
host2 = 'root@#{@nodes["control1"][:private_ip]}'
host3 = 'root@#{@nodes["control2"][:private_ip]}'

ext_routers = []
router_asn = 64512
public_vn_rtgt = 10000
public_vn_subnet = '22.2.1.1/24'

host_build = 'root@#{@nodes["config1"][:private_ip]}'

env.roledefs = {
    'all': [host1, host2, host3],
    'cfgm': [host1],
    'openstack': [host1],
    'control': [host2, host3],
    'collector': [host1],
    'webui': [host1],
    'database': [host1],
    'build': [host_build],
    'compute': [host3],
}

env.hostnames = {
    'all': ['#{@nodes["config1"][:host]}', '#{@nodes["control1"][:host]}', '#{@nodes["control2"][:host]}']
}

env.passwords = {
    host1: 'c0ntrail123',
    host2: 'c0ntrail123',
    host3: 'c0ntrail123',

    host_build: 'c0ntrail123',
}

env.ostypes = {
    host1:'ubuntu',
    host2:'ubuntu',
    host3:'ubuntu',
}

env.ntp_server = 'ntp.juniper.net'
env.openstack_admin_password = 'c0ntrail123'
env.webui_config = True
env.webui = 'firefox'
env.devstack = False
minimum_diskGB = 32
do_parallel = True

EOF
    File.open("/tmp/testbed.py", "w") { |fp| fp.puts topo }
    rcp(@nodes["config1"][:public_ip], "/tmp/testbed.py",
               "/opt/contrail/utils/fabfile/testbeds/testbed.py")
end

def copy_and_install_contrail_image (image = "/github-build/mainline/2616/ubuntu-12-04/icehouse/contrail-install-packages_3.0-2616~icehouse_all.deb")
    @nodes.each { |type, node|
        next if type =~ /vsrx/
        Process.fork {
            rcp(node[:public_ip], image)
            rsh(node[:public_ip], "dpkg -i #{File.basename image}")
            rsh(node[:public_ip], "/opt/contrail/contrail_packages/setup.sh")
        }
    }
    Process.waitall
end

def install_contrail
    rsh(@nodes["config1"][:public_ip],
        "cd /opt/contrail/utils && fab install_contrail setup_all 2>&1 > /root/fab_install.log")
end

def build_contrail_software
    sh("mkdir -p sandbox")
    sh("cd sandbox && repo init -u git@github.com:Juniper/contrail-vnc-private -m mainline/ubuntu-14-04/manifest-juno.xml")
    sh("cd sandbox && repo sync && python third_party/fetch_packages.py&& python distro/third_party/fetch_packages.py && BUILD_ONLY=1 scons -j32 src/bgp:bgp_stress_test && BUILD_ONLY=1 tools/packaging/build/packager.py --fail-on-error")
end

def setup_junos_peering
junos_config=<<EOF # root/Embe1mpls
set version "12.1I0 [xzhu]"
set system root-authentication encrypted-password "$1$DrI4JfM1$fx2W5MkiQDDJOvCvmnGjq."
set system services ssh root-login allow
set system license autoupdate url https://ae1.juniper.net/junos/key_retrieval
set interfaces ge-0/0/0 unit 0 family inet dhcp
set interfaces ge-0/0/1 unit 0
set routing-options autonomous-system 64512
set protocols bgp keep all
set protocols bgp group ibgp family inet unicast
set protocols bgp group ibgp family inet-vpn unicast
set protocols bgp group ibgp peer-as 64512
set protocols bgp group ibgp allow 192.168.0.0/16
set security forwarding-options family mpls mode packet-based
EOF
end

def configure_mx_peer
    @nodes.each { |type, node|
        next if type !~ /vsrx/

        rsh(@nodes["config1"][:public_ip],
"python /opt/contrail/utils/provision_mx.py --router_name #{node[:host]} --router_ip #{node[:private_ip]} --router_asn 64512 --api_server_ip #{@nodes["config1"][:private_ip]} --api_server_port 8082 --oper add --admin_user admin --admin_password c0ntrail123 --admin_tenant_name admin")
    }
end

def create_l2
cmds=<<EOF
import subprocess
from vnc_api.vnc_api import *
from vnc_api import vnc_api
_vnc_lib = VncApi("ci-admin", "c0ntrail123", "opencontrail-ci", "10.84.26.251", 8082, '/')
p = _vnc_lib.project_read(fq_name = ['default-domain', 'opencontrail-ci'])
vnp = vnc_api.VirtualNetworkType()
vnp.forwarding_mode = "l2"
vn = vnc_api.VirtualNetwork(name = "bgp_scale_l2", parenet_obj = p)
vn.set_virtual_network_properties(vnp)
vn.fq_name[-2] = "opencontrail-ci"
_vnc_lib.virtual_network_create(vn)
subprocess.check_output("neutron subnet-create --gateway 0.0.0.0 --tenant-id 6e432347a1d24d528a6ec78932b7bb09 --name bgp_scale_l2_subnet bgp_scale_l2 1.1.0.0/16", shell=True)
EOF
end

def run_bgp_scale_test
    commands = <<EOF
git clone -b bgp_scale https://github.com/rombie/contrail-test.git /root/contrail-test
cd /root/contrail-test/scripts/scale/control-node
export PYTHONPATH=/root/contrail-test
sshpass -p c0ntrail123 scp ci-admin@10.84.5.31:/cs-shared/bgp-scale/libtcmalloc.so.4 /usr/lib/.
sshpass -p c0ntrail123 scp ci-admin@10.84.5.31:/cs-shared/bgp-scale/bgp_stress_test /root/contrail-test/scripts/scale/control-node/.
apt-get -y install python-neutronclient python-contrail python-xmltodict python-requests contrail-lib gdb
mkdir -p /root/bgp
python flap_agent_scale_test.py -c params.ini
EOF
end

def main
    create_nodes_in_cluster
    load_nodes_from_cluster
    fix_nodes
    copy_and_install_contrail_image
    setup_topo
    install_contrail
    configure_secondary_ips
    configure_mx_peer
end

main
