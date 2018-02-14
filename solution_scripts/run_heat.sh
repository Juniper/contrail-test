
 . /contrail-test/openstackrc
export CONTRAIL_TEST_CI=$1
export PYTHONPATH=$CONTRAIL_TEST_CI:$CONTRAIL_TEST_CI/scripts/:$CONTRAIL_TEST_CI/fixtures/:/usr/local/lib/python2.7/dist-packages/:/usr/lib/python2.7/dist-packages/:$CONTRAIL_TEST_CI/tcutils/:$CONTRAIL_TEST_CI/common/:./
#python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple_heat.yaml  --delete --tenant_count 1 --tenant_index_range 11:11 --global_yaml_config_file diagnostics/csol2.global.yaml
#exit
#python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple_heat.yaml  --create --tenant_count 1 --tenant_index_range 11:11 --global_yaml_config_file diagnostics/csol2.global.yaml --heat
#exit

soln_slave_image_id=`glance image-list | grep -w soln-slave | awk -F\| '{print $2}'`
soln_slave_image_id="$(echo "${soln_slave_image_id}" | sed -e 's/^[[:space:]]*//')"

mgmt_net_id=`neutron net-list | grep -w MGMT | awk -F\| '{print$2}'`
mgmt_net_id="$(echo "${mgmt_net_id}" | sed -e 's/^[[:space:]]*//')"
mgmt_subnet_id="a95327b0-d39e-4589-8210-295f7b4a8dec"

for i in `seq 1 50`;
do
   export OS_TENANT_NAME=symantecTenant11
   heat stack-delete -y heatstack1
   deleted=0
   for ii in `seq 1 20`;
   do
     list_out=`heat stack-list`
     progress=`echo $list_out | grep -c heatstack1`
     if [ $progress -eq 1 ]
     then
       sleep 10
     else
       deleted=1
       break
     fi
   done
   if [ $deleted -eq 0 ]
   then
     echo "DELETE FAILED.."
     exit
   fi
   heat stack-create -f heat.yaml -P image_id=$soln_slave_image_id -P smgmt_id=$mgmt_subnet_id -P mgmt_id=$mgmt_net_id heatstack1
   for ii in `seq 1 10`;
   do
     list_out=`heat stack-list`
     progress=`echo $list_out | grep -c CREATE_IN_PROGRESS`
     completed=`echo $list_out | grep -c CREATE_COMPLETE`
     failed=`echo $list_out | grep -c CREATE_FAIL`
     if [ $completed -eq 1 ]
     then
       echo "CREATE_COMPLETED: Running traffic"
       break
     elif [ $progress -eq 1 ]
     then
       sleep 10
       continue
     elif [ $failed -eq 1 ]
     then
       echo "########  CREATED_FAILED #######"
       exit
     fi
   done
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple_heat.yaml  --tenant_count 1 --tenant_index_range 11:11 --global_yaml_config_file diagnostics/csol2.global.yaml --print_mgmt_ip
   sh configure_mgmt_ip.sh symantecTenant11_mgmt_ip.txt
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple_heat.yaml  --tenant_count 1 --tenant_index_range 11:11 --global_yaml_config_file diagnostics/csol2.global.yaml --traffic_only --feature_ping_only --heat
done

rm logs/tor-scale.log.log
while true;
do
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple1.yaml --delete --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol2.global.yaml 
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple1.yaml  --create --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol2.global.yaml 
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple1.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol2.global.yaml --print_mgmt_ip
   sh configure_mgmt_ip.sh symantecTenant10_mgmt_ip.txt
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple1.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol2.global.yaml --traffic_only #--feature_ping_only
  exit
done

sh configure_mgmt_ip.sh symantecTenant10_mgmt_ip.txt
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/simple1.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol2.global.yaml --traffic_only #--feature_ping_only
exit
exit

while true;
do
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count 1 --tenant_index_range 20:20 --global_yaml_config_file diagnostics/csol1.global.yaml
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create --tenant_count 1 --tenant_index_range 20:20 --global_yaml_config_file diagnostics/csol1.global.yaml
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --tenant_count 1 --tenant_index_range 20:20 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only
done
exit

exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete_global

#2.create tenant with specific name.to be safe tenant_name should be in the format tenant_name_prefix + "." + random_int
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create --tenant_count 1 --tenant_index_range 20:20 --global_yaml_config_file diagnostics/csol1.global.yaml

#3.create tenants as per yaml configuration
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create 

#4.create n tenants as per yaml.index starts from 0.
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create --tenant_count n 

#5.create n tenants as per yaml.index starts from 50.
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create --tenant_count n --tenant_index_range 50 

#6.create n tenants as per yaml.index will be random
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --create --tenant_count n --tenant_index_range 50:100 --tenant_index_random

#7.delete all tenants except standard tenants like admin,invisible
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_name=ALL

#8.delete tenant with specific name.to be safe tenant_name should be in the format tenant_name_prefix + "." + random_int
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_name=symantec.5

#9.delete tenants as per yaml configuration
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete

#10.delete n tenants as per yaml.index starts from 0.
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count n

#11.delete n tenants as per yaml.index starts from 0.
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count n --tenant_index_random

#12.delete n tenants as per yaml.index starts from 50.
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count n --tenant_index_range 50

#12.create n tenants as per yaml.index will be random
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count n --tenant_index_range 50:100 --tenant_index_random

