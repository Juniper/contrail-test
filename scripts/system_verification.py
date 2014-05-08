def verify_system_parameters(self, verification_obj):
    for projects in verification_obj['data'][1]:
        for poj_obj in verification_obj['data'][1][projects]['project']:
            #for each project in the topology verify the project parameters.
            assert verification_obj['data'][1][projects]['project'][poj_obj].verify_on_setup()
        for vn_obj in verification_obj['data'][1][projects]['vn']:
            #for each vn in all the projects in the topology verify the vn parameters.
            assert verification_obj['data'][1][projects]['vn'][vn_obj].verify_on_setup()
        for vm_obj in verification_obj['data'][1][projects]['vm']:
            #for each vm in all the projects in the topology verify the vm parameters.
            assert verification_obj['data'][1][projects]['vm'][vm_obj].verify_on_setup()
        for policy_obj in verification_obj['data'][1][projects]['policy']:
            #for each policy in all the projects in the topology verify the policies.
            assert verification_obj['data'][1][projects]['policy'][policy_obj].verify_on_setup()
#end verify_system_parameters
