from common.openstack_libs import barbican_client
import requests, json

class BarbicanHelper(object):

    def __init__(self, **kwargs):
        self.connections = kwargs.get('connections', None)
        self.barbican = barbican_client.Client(session=self.connections.auth.get_session(),
                                               region_name=self.connections.inputs.region_name)

    def create_secrets(self, name, payload, payload_content_type):
        secrets = self.barbican.secrets.create()
        secrets.name = name
        secrets.payload = payload
        secrets.payload_content_type = payload_content_type
        secrets.store()
        return secrets

    def create_container_certificate(self, container_name, cert_payload=None, cert_payload_content_type="text/plain",
        pkey_payload=None, pkey_payload_content_type="text/plain"):
        certificate = self.create_secrets(container_name+"_cert", cert_payload, cert_payload_content_type)
        pkey = self.create_secrets(container_name+"_pkey", pkey_payload, pkey_payload_content_type)
        container = self.barbican.containers.create_certificate(
            name=container_name, certificate=certificate, private_key=pkey)
        container.store()
        return container

    def delete(self, container):
        for keys in container.secrets:
            if container.secrets[keys].secret_ref:
                container.secrets[keys].delete()
        container.delete()
        
    def add_users_to_refs_acl(self, auth_token, users, entity_ref):
	url = entity_ref + '/acl'
        DEFAULT_HEADERS = {'Content-type': 'application/json; charset="UTF-8"'}
        headers = DEFAULT_HEADERS.copy()
        headers['X-AUTH-TOKEN'] = auth_token
        data = {}
        data['read'] = {}
        data['read']['users'] = users
        resp = requests.patch(url, data=json.dumps(data), headers=headers)
        return resp.status_code
        

def setup_test_infra():
    import logging
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('event')
    logger.setUp()
    mylogger = logger.logger
    from common.connections import ContrailConnections
    connections = ContrailConnections(logger=mylogger)
    return connections

def main():
    import sys
    conn = setup_test_infra()

    #secret = Secrets(connections=conn, container_name='tls_container', secret_name='cert', secret_payload='test')
    #secret.create_secret_store()
    #secret_ref = secret.get_secret_ref()
    #secrets = list()
    #secrets.append(['secret1', secret_ref])
    #secret.create_container('container1', 'certificate', secrets)

    container = Container(connections=conn, container_name='tls_container', cert_name='certificate', cert_payload='certificate',
        pkey_name='private_key', pkey_payload='priavte_key')
    #container.create_secret_cert()
    #container.create_secret_pkey()
    container.setUp()
    tls_container = container.create_container_certificate()
    import pdb;pdb.set_trace()
    #print container.get_container_ref()
    #print container.get_secret_ref(container.certificate)
    #print container.get_container_certificate()
    #print container.get_secret_ref(container.pkey)
    #print container.get_container_private_key()
    container.create_acls(container.get_secret_ref(container.certificate), ['0f60dd927db34534833b04192342f845'], '854589113eb449b1ac623fd5a134b369')


if __name__ == "__main__":
    main()
