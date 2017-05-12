
. /etc/contrail/openstackrc
export CONTRAIL_TEST_CI=$1
export PYTHONPATH=$CONTRAIL_TEST_CI:$CONTRAIL_TEST_CI/scripts/:/usr/lib/python2.7/dist-packages/:/root/sol_test//lib/python2.7/site-packages/:$CONTRAIL_TEST_CI/fixtures/:$CONTRAIL_TEST_CI/tcutils/:$CONTRAIL_TEST_CI/common/:./

rm logs/tor-scale.log.log
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count 1 --tenant_index_range 25:25 --global_yaml_config_file diagnostics/csol1.global.yaml 
#exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --create --tenant_count 1 --tenant_index_range 25:25 --global_yaml_config_file diagnostics/csol1.global.yaml
#exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --tenant_count 1 --tenant_index_range 25:25 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only --feature_ping_only
exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --delete --tenant_count 30 --tenant_index_range 30:60 --global_yaml_config_file diagnostics/csol1.global.yaml
exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --tenant_count 30 --tenant_index_range 30:60 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only --feature_ping_only
exit
while true;
do
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --delete --tenant_count 2 --tenant_index_range 30:60 --global_yaml_config_file diagnostics/csol1.global.yaml
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --create --tenant_count 2 --tenant_index_range 30:60 --global_yaml_config_file diagnostics/csol1.global.yaml
exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.bgp_ntt.yaml --tenant_count 2 --tenant_index_range 30:60 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only

done
