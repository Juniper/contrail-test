from fabfile.config import testbed

def get_live_migration_enable():
    return getattr(testbed, 'live_migration', False)

def get_live_migration_opts():
    live_migration_opts = "disabled"
    if get_live_migration_enable():
        live_migration_opts = "enabled"
    return live_migration_opts
