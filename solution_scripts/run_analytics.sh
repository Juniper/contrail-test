
. /etc/contrail/openstackrc
export CONTRAIL_TEST_CI=$1
export PYTHONPATH=$CONTRAIL_TEST_CI:$CONTRAIL_TEST_CI/scripts/:/usr/lib/python2.7/dist-packages/:/root/sol_test//lib/python2.7/site-packages/:$CONTRAIL_TEST_CI/fixtures/:$CONTRAIL_TEST_CI/tcutils/:$CONTRAIL_TEST_CI/common/:./

rm logs/tor-scale.log.log

KEYSTONE_TOKEN="356f09e8f0004b10a97a2bd4f0fd85f1"

## curl -s -H "X-Auth-Token:356f09e8f0004b10a97a2bd4f0fd85f1" http://172.16.70.3:8081/analytics/uves | python -m json.tool
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.tor2.si.v4.v1.yaml --analytics --global_yaml_config_file diagnostics/csol1.global.yaml --keystone_token $KEYSTONE_TOKEN
