from fabfile.config import testbed

def get_collector_syslog_port():
    return getattr(testbed, 'collector_syslog_port', None)
#end get_collector_syslog_port

def get_database_ttl():
    return getattr(testbed, 'database_ttl', None)
#end get_database_ttl

def get_database_dir():
    return getattr(testbed, 'database_dir', None)
#end get_database_dir
