#!/usr/bin/env bash
# Tool to bringup and manage openvswitch switches
# Currenlty supported on Ubuntu 14.04 only
# Usage Example:
# bash -x contrail-ovs-tool.sh --name br0 -t 10.204.216.195  -r ssl:10.204.216.184:6632  -p /root/sc-privkey.pem -c /root/sc-cert.pem -b /tmp/br0-cacert.pem  -T init

# Note : Only one instance of openvswitch is runnable on a node
# An attempt was made where multiple independent openvswitch could run on the same node
# The intention was to use the same node for multiple testbeds
# But once a second ovs-vswitchd/ovsdb-server was started, the bridge interfaces were 
# getting removed from kernel and would never get added again
# Possibly, similar to http://openvswitch.org/pipermail/discuss/2013-April/009623.html
# 

ovs_path="/usr/share/openvswitch/"
function usage {
    echo "Usage: $0 [OPTION]..."
    echo "Setup openvswitch"

    echo "-n, --name 		Name of the openvswitch"
    echo "-t, --tunnel-ip 	Tunnel IP "
    echo "-R, --restart		Restart ovs processes"
    echo "-r, --remote 		Remote ip (ptcp/ssl connect string)"
    echo "-p, --privkey 	private key file path"
    echo "-c, --certprivkey	cert for private key file path"
    echo "-b, --bootstrap-ca-cert		Bootstrap CA Cert file path"
    echo "-T, --task 		one of stop, start, restart, init"
    echo ""
}
    

if ! options=$(getopt -o hn:t:Rr:p:c:b:T: -l help,name:,tunnel-ip:,restart,remote:,privkey:,certprivkey:,bootstrap-ca-cert:task: -- "$@")
then
    # parse error
    usage
    exit 1
fi

restart=0
task="init_ovs"

eval set -- $options
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit;;
    -n|--name) name=$2; shift;;
    -t|--tunnel-ip) tunnel_ip=$2; shift;;
    -R|--restart) restart=1;;
    -r|--remote) remote=$2; shift;;
    -p|--privkey) privkey=$2; shift;;
    -c|--certprivkey) certprivkey=$2; shift;;
    -b|--bootstrap-ca-cert) bootstrap_ca=$2; shift;;
    -T|--task) task=$2; shift;;
  esac
  shift
done

echo "remote : $remote"
echo "privkey: $privkey"
echo "pubkey: $certprivkey"
echo "Boostrap-ca-cert : $bootstrap_ca"
echo "tunnel ip : $tunnel_ip"
echo "name : $name"
    
function die
{
    local message=$1
    [ -z "$message" ] && message="Died"
    echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}: $message." >&2
    exit 1
}

function add_repo {
    repo_string="deb http://ppa.launchpad.net/vshn/openvswitch/ubuntu trusty main"
    grep -q "$repo_string" /etc/apt/sources.list || (echo "$repo_string" >> /etc/apt/sources.list && apt-get update)
}

function install_openvswitch {
    apt-get -y --force-yes install openvswitch-switch openvswitch-common openvswitch-vtep openvswitch-datapath-dkms python-openvswitch || die "Unable to install openvswitch"
}

function start_vswitch_procs {
    cmd_args=""
    if test -n $privkey; then
        cmd_args=$cmd_args" -p "$privkey
    fi
    if test -n $certprivkey; then
        cmd_args=$cmd_args" -c "$certprivkey
    fi
    if test -n $bootstrap_ca; then
        cmd_args=$cmd_args" --bootstrap-ca-cert="$bootstrap_ca
    fi
    ovsdb-server --pidfile=/var/run/openvswitch/ovsdb-server-${name}.pid --detach --log-file=/var/log/openvswitch/ovsdb-server-${name}.log -vinfo --remote=punix:/var/run/openvswitch/db-${name}.sock --remote=db:hardware_vtep,Global,managers --remote=$remote $cmd_args /etc/openvswitch/ovs-${name}.db /etc/openvswitch/vtep-${name}.db
    common_arg=" --db unix:/var/run/openvswitch/db-${name}.sock "
    #ovs-vsctl $common_arg set-controller $name punix:/var/run/openvswitch/${name}.controller
    sleep 5
    ovs-vswitchd --log-file=/var/log/openvswitch/ovs-vswitchd-${name}.log -vinfo --pidfile=ovs-vswitchd-${name}.pid unix:/var/run/openvswitch/db-${name}.sock --detach
    sleep 5
    ovs-vsctl $common_arg add-br $name
    ifconfig $name up
    vtep-ctl $common_arg add-ps $name
    vtep-ctl $common_arg set Physical_Switch $name tunnel_ips=$tunnel_ip
    python $ovs_path/scripts/ovs-vtep $common_arg --log-file=/var/log/openvswitch/ovs-vtep-${name}.log -v info --pidfile=/var/run/openvswitch/ovs-vtep-${name}.pid --detach $name
}

function stop_vswitch_procs {
    # Stop ovsdb-server
    pid_folder="/var/run/openvswitch"
    pkill -f ovs-${name}.db
    rm -f $pid_folder/ovsdb-server-${name}.pid
    # Stop ovs-vswitchd
    pkill -f db-${name}.sock
    rm -f $pid_folder/ovs-vswitchd-${name}.pid
    # Stop ovs-vtep
    pkill -f ovs-vtep-${name}.pid
    rm -f $pid_folder/ovs-vtep-${name}.pid
    service openvswitch-switch stop
    sleep 2
}

function setup_openvswitch {
    stop_vswitch_procs
    rm -f /etc/openvswitch/ovs-${name}*.db /etc/openvswitch/vtep-${name}.db
    ovsdb-tool create /etc/openvswitch/ovs-${name}.db $ovs_path/vswitch.ovsschema 
    ovsdb-tool create /etc/openvswitch/vtep-${name}.db $ovs_path/vtep.ovsschema

    start_vswitch_procs
     
}

function check_supported_platform {
    if [ -f /etc/lsb-release ]; then
        grep -q "14.04" /etc/lsb-release || die "Supported only on Ubuntu 14.04 "
    else
        die "Supported only on Ubuntu 14.04 "
    fi
}

function init_ovs {
    check_supported_platform
    add_repo
    echo "manual" > /etc/init/openvswitch-vswitch.override
    install_openvswitch
    setup_openvswitch
}

function restart_ovs {
    stop_vswitch_procs
    start_vswitch_procs
}

function stop_ovs { 
    stop_vswitch_procs
}

function start_ovs { 
    start_vswitch_procs
}


case $task in
   "init")   init_ovs
   ;;
   "restart") restart_ovs
   ;;
   "stop") stop_ovs
   ;;
   "start") start_ovs
   ;;
esac
