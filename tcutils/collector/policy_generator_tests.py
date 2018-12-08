import requests

class PolicyGeneratorClient:

    def __init__(self, connections):
        self.connections = connections
        self.inputs = self.connections.inputs
        self.logger = self.connections.logger
        self.urls = self._get_urls()

    def _get_urls(self):
        port = self.inputs.policy_generator_port 
        if self.inputs.internal_vip:
            ips = [self.inputs.internal_vip]
        else:
            #TODO: use self.inputs.security_apps_ips
            ips = self.inputs.collector_ips
        return ['http://%s:%s/security-apps/policy-generation' % (ip, port) for ip in ips]

    #TODO: exception handling and retry
    def _post_request(self, query_params):
        urls = self.urls
        resp = requests.post(urls[0], json=query_params)
        return resp.json()

    def generate_policy(self, query_params):
        self.logger.info('query: %s' % query_params)
        resp = self._post_request(query_params)
        return resp