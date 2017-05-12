
. /etc/contrail/openstackrc

export CONTRAIL_TEST_CI=$1
export PYTHONPATH=$CONTRAIL_TEST_CI:$CONTRAIL_TEST_CI/scripts/:/usr/lib/python2.7/dist-packages/:/root/sol_test//lib/python2.7/site-packages/:$CONTRAIL_TEST_CI/fixtures/:$CONTRAIL_TEST_CI/tcutils/:$CONTRAIL_TEST_CI/common/:./

rm logs/tor-scale.log.log


#1.create and delete global configuration
#python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --global_yaml_config_file diagnostics/csol1.global.yaml --delete_global
#exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --global_yaml_config_file diagnostics/csol1.global.yaml --create_global
exit
