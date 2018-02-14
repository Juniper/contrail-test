
 . /contrail-test/openstackrc
export CONTRAIL_TEST_CI=$1
export PYTHONPATH=$CONTRAIL_TEST_CI:$CONTRAIL_TEST_CI/scripts/:$CONTRAIL_TEST_CI/fixtures/:/usr/local/lib/python2.7/dist-packages/:/usr/lib/python2.7/dist-packages/:$CONTRAIL_TEST_CI/tcutils/:$CONTRAIL_TEST_CI/common/:./
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only --feature_ping_only
exit
#
rm logs/tor-scale.log.log
while true;
do
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --delete --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol1.global.yaml
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml  --create --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol1.global.yaml 
   #python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol1.global.yaml --print_mgmt_ip
   #sh configure_mgmt_ip.sh symantecTenant10_mgmt_ip.txt
   exit
   python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --tenant_count 1 --tenant_index_range 10:10 --global_yaml_config_file diagnostics/csol1.global.yaml --traffic_only #--feature_ping_only
exit
done

