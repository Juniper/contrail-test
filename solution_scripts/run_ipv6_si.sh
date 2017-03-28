
. /etc/contrail/openstackrc
export PYTHONPATH=./fixtures:./scripts:./:./vnc_api-0.1dev:./cfgm_common-0.1dev:/usr/lib/python2.7/dist-packages/
rm logs/tor-scale.log.log

while true;
do
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.tor2.si.ipv6.v1.yaml --delete --tenant_count 1 --tenant_index_range 70:70 --global_yaml_config_file diagnostics/csol1.global.yaml
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.tor2.si.ipv6.v1.yaml --create --tenant_count 1 --tenant_index_range 70:70 --global_yaml_config_file diagnostics/csol1.global.yaml --dpdk
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.tor2.si.ipv6.v1.yaml --tenant_count 1 --tenant_index_range 70:70 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only
done
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

