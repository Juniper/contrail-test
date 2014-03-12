from fabfile.config import testbed
from fabric.api import env

def get_mt_enable():
    return getattr(testbed, 'multi_tenancy', False)
#end _get_mt_ena

def get_mt_opts():
    mt_opts = ''
    if get_mt_enable():
        u = getattr(testbed, 'os_username', 'admin')
        p = getattr(env, 'openstack_admin_password', 'contrail123')
        t = getattr(testbed, 'os_tenant_name', 'admin')
        if not u or not p or not t:
            raise Exception('Admin user, password and tenant must be defined if multi tenancy is enabled')
        mt_opts = " --admin_user %s --admin_password %s --admin_tenant_name %s" %(u, p, t)
    return mt_opts
