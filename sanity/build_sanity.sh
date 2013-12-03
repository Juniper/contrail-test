
#!/usr/bin/env bash -x 

#Self IP 
IP=$1

# Drop any nova mysql tables since, due to bugs, some VMs stay alive
sudo systemctl stop  openstack-nova-api.service
sudo systemctl stop  openstack-nova-objectstore.service
sudo systemctl stop  openstack-nova-compute.service
sudo systemctl stop  openstack-nova-scheduler.service
if [ -f /etc/contrail/mysql.token ] ; 
then 
    token=`cat /etc/contrail/mysql.token` ;  
    mysql -u root --password=$token -e 'drop database nova;';
fi

#WA for bug 132 
rm -f /var/lib/nova/tmp/nova-iptables

sudo yum clean all 

sudo rm -f /var/log/libvirt/qemu/instance*
sudo rm -f /var/lib/nova/instances/instance-*
sudo rm -f /var/log/libvirt/qemu/inst*

sudo yum clean all
#sudo yum -y --exclude=contrail-setup* update 
sudo yum -y  update 
cd /opt/contrail/contrail_installer
export PASSWORD=contrail123
./setup-vnc-cfgm.py --self_ip $IP --collector_ip $IP
./setup-vnc-control.py --self_ip $IP --cfgm_ip $IP --collector_ip $IP

yum -y remove contrail-agent
sleep 20
yum -y install contrail-agent 
cat /etc/contrail/agent.conf
cat /etc/contrail/agent_param
echo ""
echo ""

#Lets reset config each time
sudo sed -i 's/api_server.conf$/api_server.conf --reset_config/' /usr/lib/systemd/system/contrail-api.service 
sudo systemctl --system daemon-reload


sudo reboot

#python /root/stuff/scripts/tests/test_sanity.py params-57.ini


