# import handling for quantum & neutron
try:
    from quantumclient.quantum import client as quantum_client
    from quantumclient.client import HTTPClient as quantum_http_client
    from quantumclient.common import exceptions as quantum_exception
    from quantumclient.common.exceptions import QuantumClientException as quantum_client_exception
except:
    quantum_client = None
    quantum_http_client = None
    quantum_exception = None
    quantum_client_exception = None
    
try:
    from neutronclient.neutron import client as neutron_client
    from neutronclient.client import HTTPClient as neutron_http_client
    from neutronclient.common import exceptions as neutron_exception
    from neutronclient.common.exceptions import NeutronClientException as neutron_client_exception
except:
    neutron_client = None
    neutron_http_client = None
    neutron_exception = None
    neutron_client_exception = None

network_client = quantum_client if quantum_client else neutron_client
network_http_client = quantum_http_client if quantum_http_client else neutron_http_client
network_exception = quantum_exception if quantum_exception else neutron_exception
if quantum_client_exception:
    network_client_exception = quantum_client_exception
elif neutron_client_exception:
    network_client_exception = neutron_client_exception
else:
    network_client_exception = Exception

# import handling for keystone
try:
    from keystoneclient.v2_0 import client as ks_client
    from keystoneclient import exceptions as ks_exceptions
    from keystoneclient.auth.identity import v2 as ks_auth_identity_v2
    from keystoneclient import session as ks_session
    import keystoneclient
except:
    ks_client = None
    ks_exceptions = None
    keystoneclient = None
    ks_auth_identity_v2 = None
    ks_session = None

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
