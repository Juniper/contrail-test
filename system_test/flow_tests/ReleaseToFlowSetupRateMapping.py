# Here the rate is set for Policy flows, local to a compute, which is
# lesser than policy flows across computes
expected_flow_setup_rate = {}
expected_flow_setup_rate['policy'] = {
    '1.04': 6000, '1.05': 9000, '1.06': 10000, '1.10': 10000}
expected_flow_setup_rate['nat'] = {'1.04': 4200,
                                   '1.05': 6300, '1.06': 7500, '1.10': 7500}
