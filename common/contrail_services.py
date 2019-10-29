_CONTRAIL_SERVICES_OPENSHIFT_CONTAINER_MAP = {
    # Config
    'api-server': ['k8s_contrail-controller-config-api'],
    'schema': ['k8s_contrail-controller-config-schema'],
    'svc-monitor': ['k8s_contrail-controller-config-svcmonitor'],
    'device-manager': ['k8s_contrail-controller-config-devicemgr'],
    'config-rabbitmq': ['k8s_rabbitmq_contrail-configdb'],
    'config-zookeeper': ['k8s_config-zookeeper'],
    'config-cassandra': ['k8s_contrail-configdb'],
    # Control
    'control': ['k8s_contrail-controller-control_'],
    'dns': ['k8s_contrail-controller-control-dns_'],
    'named': ['k8s_contrail-controller-control-named_'],
    # Analytics
    'analytics-api':['k8s_contrail-analytics-api'],
    'query-engine': ['k8s_contrail-analytics-query-engine'],
    'collector': ['k8s_contrail-analytics-collector'],
    'analytics-zookeeper': [],
    'analytics-cassandra': ['k8s_contrail-analyticsdb'],
    'stunnel': ['stunnel'],
    # Vrouter
    'agent-dpdk': [],
    'agent': ['k8s_contrail-vrouter-agent'],
    # Node managers
    'vrouter-nodemgr': ['k8s_contrail-agent-nodemgr'],
    'config-nodemgr': ['k8s_contrail-controller-config-nodemgr'],
    'analytics-nodemgr': ['k8s_contrail-analytics-nodemgr'],
    'control-nodemgr': ['k8s_contrail-controller-control-nodemgr'],
    'configdb-nodemgr': ['k8s_contrail-config-database-nodemgr'],
    'analyticsdb-nodemgr': ['k8s_contrail-analyticsdb-nodemgr'],
    # Openshift master
    'contrail-kube-manager': ['k8s_contrail-kube-manager'],
    'kube-apiserver':  ['kube-apiserver'],
    # Web UI
    'redis': ['k8s_redis_redis'],
    'webui': ['k8s_contrail-controller-webui-web'],
    'webui-middleware': ['k8s_contrail-controller-webui-job'],
}

_CONTRAIL_SERVICES_CONTAINER_MAP = {
    'api-server': ['config_api', 'contrail-config-api'],
    'schema': ['config_schema', 'contrail-schema-transformer'],
    'svc-monitor': ['config_svcmonitor', 'contrail-svcmonitor', 'config_svc_monitor'],
    'device-manager': ['config_devicemgr', 'contrail-devicemgr', 'device_manager'],
    'control': ['control_control', 'k8s_contrail-control'],
    'dns': ['control_dns', 'contrail-dns'],
    'named': ['control_named', 'contrail-named'],
    'analytics-api': ['analytics_api', 'contrail-analytics-api'],
    'query-engine': ['analytics_query-engine', 'contrail-query-engine', 'analytics_queryengine',
                     'analytics_database_query-engine', 'analytics_database_queryengine'],
    'collector': ['analytics_collector', 'contrail-collector'],
    'agent-dpdk': ['agent-dpdk'],
    'agent': ['contrail-agent', 'vrouter-agent', 'contrail-vrouter-agent', 'vrouter_agent'],
    'webui': ['webui_web', 'contrail-webui_'],
    'webui-middleware': ['webui_job', 'contrail-webui-middleware'],
    'config-rabbitmq': ['configdatabase_rabbitmq', 'rabbitmq'],
    'config-zookeeper': ['configdatabase_zookeeper',
                         'contrail-config-zookeeper', 'config_database_zookeeper', 'config_zookeeper'],
    'config-cassandra': ['configdatabase_cassandra', 'contrail-configdb', 'config_database_cassandra', 'config_database'],
    'analytics-zookeeper': ['analyticsdatabase_zookeeper',
                            'contrail-analytics-zookeeper', 'analytics_database_zookeeper', 'analytics_zookeeper'],
    'analytics-cassandra': ['analyticsdatabase_cassandra',
                            'contrail-analyticsdb', 'analytics_database_cassandra', 'contrail_analytics_database'],
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
    'redis': ['webui_redis', 'webui-redis','redis'],
    'stunnel': ['stunnel'],
    'vrouter-nodemgr': ['vrouter_nodemgr', 'vrouter-nodemgr', 'vrouter_agent_nodemgr'],
    'config-nodemgr': ['config_nodemgr', 'config-nodemgr'],
    'analytics-nodemgr': ['analytics_nodemgr', 'analytics-nodemgr'],
    'control-nodemgr': ['control_nodemgr', 'control-nodemgr'],
    'analyticsdb-nodemgr': ['analyticsdatabase_nodemgr',
                            'analyticsdb-nodemgr', 'analytics_database_nodemgr'],
    'contrail-kube-manager': ['contrail-kube-manager', 'kubemanager'],
    'kube-apiserver':  ['kube-apiserver'],
    'strongswan':  ['strongswan_strongswan']
}

CONTRAIL_PODS_SERVICES_MAP = {
    'vrouter' : ['vrouter-nodemgr', 'agent'],
    'control' : ['control-nodemgr',
                 'control',
                 'named',
                 'dns'],
    'config' : ['config-nodemgr',
                'api-server',
                'schema',
                'svc-monitor',
                'device-manager'],
    'config-database' : ['config-cassandra',
                         'config-zookeeper',
                         'config-rabbitmq'],
    'analytics' : ['analytics-nodemgr',
                   'analytics-api',
                   'collector'],
    'analytics-database' : ['analytics-cassandra',
                            'analyticsdb-nodemgr',
                            'query-engine'],
    'webui' : ['webui', 'webui-middleware', 'redis'],
    'kubernetes' : ['contrail-kube-manager'],
}

BackupImplementedServices = ["schema",
                             "svc-monitor",
                             "device-manager",
                             "contrail-kube-manager"]
ServiceHttpPortMap = {
    "agent" : 8085,
    "control" : 8083,
    "collector" : 8089,
    "query-engine" : 8091,
    "analytics-api" : 8090,
    "dns" : 8092,
    "api-server" : 8084,
    "schema" : 8087,
    "svc-monitor" : 8088,
    "device-manager" : 8096,
    "analytics-nodemgr" : 8104,
    "vrouter-nodemgr" : 8102,
    "control-nodemgr" : 8101,
    "analyticsdb-nodemgr" : 8103,
    "config-nodemgr" : 8100,
    "snmp-collector" : 5920,
    "topology" : 5921,
    "contrail-kube-manager" : 8108,
}

ANSIBLE_DEPLOYER_PODS_DIR = {
    "vrouter": "/etc/contrail/vrouter",
    "config": "/etc/contrail/config",
    "control": "/etc/contrail/control",
    "analytics": "/etc/contrail/analytics",
    "analytics-database": "/etc/contrail/analytics_database",
    "strongswan": "/etc/contrail/vrouter/strongswan"
}

ANSIBLE_DEPLOYER_PODS_YML_FILE = {
    "strongswan": "strongswan_compose.yml"
}

def get_contrail_services_map(inputs):
    if inputs.deployer == 'openshift':
        return _CONTRAIL_SERVICES_OPENSHIFT_CONTAINER_MAP
    else:
        return _CONTRAIL_SERVICES_CONTAINER_MAP