from common.base import GenericTestBase
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.creator import ServiceChainCreator
from common.servicechain.firewall.verify import VerifySvcFirewall


class TestSVCCombosForEvpn(GenericTestBase, VerifySvcFirewall):

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 3:
            return (False, 'Need atleast 3 compute nodes')
        return (True, None)

    @preposttest_wrapper
    def test_evpn_svc_combo_1(self):
        '''
        Example testcase to show input-driven svc chaining test
        '''
        data = {
            'left_vm': {
                'host': self.inputs.compute_names[0],
            },
            'right_vm': {
                'host': self.inputs.compute_names[1],
            },
            'policy': [
                {
                    'proto': 'any',
                    'services': [
                        {'service_mode': 'transparent',
                         'si_count': 1,
                         'hosts': [self.inputs.compute_names[2]]
                         },
                        {'service_mode': 'in-network',
                         'si_count': 2,
                         'hosts': [self.inputs.compute_names[1],
                                   self.inputs.compute_names[0]]
                         }
                    ]
                }
            ]
        }
        svc_creator = ServiceChainCreator(self)
        svc_chain_info = svc_creator.build(data, evpn=True)
        assert self.verify_svc_chain(svc_chain_info=svc_chain_info)

    def _do_cleanup(self):
        while self._cleanups:
            cleanup, args, kwargs = self._cleanups.pop(-1)
            try:
                cleanup(*args, **kwargs)
            except Exception:
                raise

    @preposttest_wrapper
    def test_evpn_svc_combo_all(self):
        '''
        Run all possible host combinations in a svc-chain with
        max 2 SIs in each stage and max stages as 2

        '''
        svc_creator = ServiceChainCreator(self)
        left_vm_nodes = [self.inputs.compute_names[0]]
        right_vm_nodes = [self.inputs.compute_names[2]]
        si_vm_nodes = self.inputs.compute_names[:]
        for combo in svc_creator.get_next_combo(
                left_vm_nodes=left_vm_nodes,
                right_vm_nodes=right_vm_nodes,
                si_vm_nodes=si_vm_nodes,
                si_modes=['transparent', 'in-network', 'in-network-nat'],
                max_sis=2,
                max_stages=2):
            self.logger.info('Combo : %s' % (combo))
            svc_chain_info = svc_creator.build(combo, evpn=True)
            svc_chain = self.verify_svc_chain(svc_chain_info=svc_chain_info)
            self._do_cleanup()
