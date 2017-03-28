
. /etc/contrail/openstackrc
export PYTHONPATH=./fixtures:./scripts:./:./vnc_api-0.1dev:./cfgm_common-0.1dev:/usr/lib/python2.7/dist-packages/
rm logs/tor-scale.log.log


#1.create and delete global configuration
#python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --global_yaml_config_file diagnostics/csol1.global.yaml --delete_global
#exit
python diagnostics/systemtest.full.py --ini_file diagnostics/global_params.ini --yaml_config_file diagnostics/symantec.full.yaml --global_yaml_config_file diagnostics/csol1.global.yaml --create_global
exit
