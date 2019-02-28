import logging as LOG
from tcutils.verification_util import VerificationUtilBase

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

class PolicyGeneratorClient(VerificationUtilBase):

    def __init__(self, inputs, logger=LOG):
        port = inputs.policy_generator_port
        ip = inputs.policy_generator_ips[0]
        super(PolicyGeneratorClient, self).__init__(ip, port, protocol='http',
                base_url='/security-apps/',
                insecure=True, args=inputs, logger=logger)

    def generate_policy(self, query_params):
        return self.post(query_params, path='policy-generation')