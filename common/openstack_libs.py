# import handling for neutron
try:
    from neutronclient.neutron import client as neutron_client
    from neutronclient.client import HTTPClient as neutron_http_client
    from neutronclient.common.exceptions import NeutronClientException as neutron_client_exception
    from neutronclient.common import exceptions as neutron_exception
except:
    neutron_client = None
    neutron_http_client = None
    neutron_client_exception = None
    neutron_exception = None

# import handling for keystone 
try:
    from keystoneauth1 import identity as ks_identity
    from keystoneauth1 import session as ks_session
except ImportError:
    try:
        from keystoneclient.auth import identity as ks_identity
        from keystoneclient import session as ks_session
    except ImportError:
        ks_identity = None
        ks_session = None
try:
    from keystoneclient import client as ks_client
    from keystoneclient import exceptions as ks_exceptions
except:
    ks_client = None
    ks_exceptions = None

# import handling for nova
try:
    from novaclient import client as nova_client
    from novaclient import exceptions as nova_exception
except:
    nova_client = None
    nova_exception = None

# import handling for ceilometer
try:
    from ceilometerclient import client as ceilo_client
except:
    ceilo_client = None

try:
    from glanceclient import Client as glance_client
except:
    glance_client = None

try:
    from heatclient import client as heat_client
except:
    heat_client = None

try:
    from barbicanclient import barbican_client
except:
    barbican_client = None
