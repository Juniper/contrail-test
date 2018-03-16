from collections import OrderedDict


SERVICES_MAP = OrderedDict({'api-server': ['config_api', 'contrail-config-api'],
                'schema': ['config_schema', 'contrail-schema-transformer'],
                'svc-monitor': ['config_svcmonitor', 'contrail-svc-monitor'],
                'device-manager': ['config_devicemgr', 'contrail-devicemgr'],
                'control': ['control_control', 'contrail-control'],
                'dns': ['control_dns', 'contrail-dns'],
                'named': ['control_named', 'contrail-named'],
                'analytics-api': ['analytics_api', 'contrail-analytics-api'],
                'alarm-gen': ['analytics_alarm-gen', 'contrail-alarm-gen'],
                'query-engine': ['analytics_query-engine', 'contrail-query-engine'],
                'topology': ['analytics_topology', 'contrail-topology'],
                'collector': ['analytics_collector', 'contrail-collector'],
                'snmp-collector': ['analytics_snmp-collector', 'contrail-snmp-collector'],
                'agent': ['contrail-agent', 'vrouter-agent', 'contrail-vrouter-agent'],
                'webui': ['webui_web', 'contrail-webui'],
                'webui-middleware': ['webui_job', 'contrail-webui-middleware'],
                'config-rabbitmq': ['configdatabase_rabbitmq', 'rabbitmq'],
                'config-zookeeper': ['configdatabase_zookeeper', 'contrail-config-zookeeper'],
                'config-cassandra': ['configdatabase_cassandra', 'contrail-configdb'],
                'analytics-kafka': ['analyticsdatabase_kafka', 'contrail-kafka'],
                'analytics-zookeeper': ['analyticsdatabase_zookeeper', 'contrail-analytics-zookeeper'],
                'analytics-cassandra': ['analyticsdatabase_cassandra', 'contrail-analyticsdb'],
                'nova': ['nova_api', 'nova-api-osapi'],
                'nova-compute': ['nova_compute', 'nova-compute'],
                'nova-conductor': ['nova_conductor', 'nova-conductor'],
                'nova-scheduler': ['nova_scheduler', 'nova-scheduler'],
                'glance': ['glance_api', 'glance-api'],
                'rabbitmq': ['rabbitmq'],
                'haproxy': ['haproxy'],
                'keystone': ['keystone-api', 'keystone'],
                'neutron': ['neutron', 'neutron-server'],
                'mysql': ['mariadb'],
                'redis': ['webui_redis', 'webui-redis'],
                'vrouter-nodemgr': ['vrouter_nodemgr', 'vrouter-nodemgr'],
                'config-nodemgr': ['config_nodemgr', 'config-nodemgr'],
                'analytics-nodemgr': ['analytics_nodemgr', 'analytics-nodemgr'],
                'control-nodemgr': ['control_nodemgr', 'control-nodemgr'],
                'configdb-nodemgr': ['configdatabase_nodemgr', 'configdatabase-nodemgr'],
                'analyticsdb-nodemgr': ['analyticsdatabase_nodemgr', 'analyticsdatabase-nodemgr'],
                'contrail-kube-manager': ['contrail-kube-manager'],
               })
# Added below for backward compatibility and can be removed
# once all deployments move to microservices model
SERVICES_MAP['controller'] = ['contrail-controller']
SERVICES_MAP['analytics'] = ['contrail-analytics']
SERVICES_MAP['analyticsdb'] = ['contrail-analyticsdb']
