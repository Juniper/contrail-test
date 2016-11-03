from tcutils.util import *
from vn_test import *
from policy_test import *
from alarm_test import *

class VerifyAlarms():

    def verify_alarm_config(self,parent_type='project'):
        exp1 = {'operation': '<=','operand1': "UveVirtualNetworkConfig.total_acl_rules",'operand2':{'json_value': '2'}}
        exp2 = {'operation': '>=','operand1': 'UveVirtualNetworkConfig.total_acl_rules','operand2':{'json_value': '1'}}
        alarm_name = 'vn_acl_rule'
        uve_keys = ['virtual-network']
        vn_pol_list=[]
        alarm_fix = self.create_alarm([exp1],alarm_name,uve_keys,parent_type=parent_type)
        assert alarm_fix.verify_alarm_setup()
        vn_pol_dict=self.create_vn_policy_config()
        assert self.analytics_obj.verify_vn_acl_alarm(),'Alarm not raised'
        self.logger.info('Update alarm with new rules')
        assert alarm_fix.set_alarm_rules([exp2]),'set alarm rules failed'
        sleep(15)
        assert alarm_fix.verify_alarm_setup()
        assert self.analytics_obj.verify_vn_acl_alarm(),'Alarm not raised'
        vn_pol_dict['vn_fixture'].unbind_policies(vn_pol_dict['vn_fixture'].vn_id)
        assert self.analytics_obj.verify_vn_acl_alarm(verify_alarm_cleared=True),'Alarm not cleared'
    # end verify_alarm_config

    def verify_conf_with_invalid_cases(self, parent_type='project'):
        exp1 = {'operation': '<=','operand1': "UveVirtualNetworkConfig.total_acl_rules",'operand2':{'json_value': '2'}}
        alarm_name = 'vn_acl_rule'
        uve_keys = ['virtual-network']
        alarm_fix = self.create_alarm([exp1],alarm_name,uve_keys,parent_type=parent_type)
        assert alarm_fix.verify_alarm_setup()
        assert not alarm_fix.set_alarm_severity('50'),'Severity should not be allowed to set 50'
        assert not alarm_fix.set_alarm_rules([]),'Empty alarm rules should not be allowed'
        assert not alarm_fix.set_uve_keys(['invalid_key']),'Invalid UVE keys should not be allowed'
        assert not alarm_fix.set_uve_keys([]),'Empty UVE keys should not be allowed'
        exp3= {'operation': '>==','operand1': 'UveVirtualNetworkConfig.total_acl_rules','operand2':{'json_value': '1'}}
        assert not alarm_fix.set_alarm_rules([exp3]),'Invalid operation should not be allowed'
    #end verify_conf_with_invalid_cases

    def verify_alarm_conf_with_multiple_rules(self, parent_type= 'project'):
        exp1 = {'operation': '<=','operand1': "UveVirtualNetworkConfig.total_acl_rules",'operand2':{'json_value': '2'}}
        exp2 = {'operation': '>=','operand1': 'UveVirtualNetworkConfig.total_acl_rules','operand2':{'json_value': '1'}}
        exp3 = {'operation': '==','operand1': 'UveVirtualNetworkConfig.total_acl_rules','operand2':{'json_value': '1'}}
        alarm_name = 'vn_acl_rule'
        uve_keys = ['virtual-network']
        vn_pol_list=[]
        self.logger.info('Create alarm_config rules with multiple And conditions')
        alarm_fix = self.create_alarm([exp1,exp2,exp3],alarm_name,uve_keys,parent_type)
        assert alarm_fix.verify_alarm_setup()
        vn_pol_dict=self.create_vn_policy_config()
        assert self.analytics_obj.verify_vn_acl_alarm(),'Alarm not raised'
        self.logger.info('Update alarm with new And rules')
        exp2 = {'operation': '>=','operand1': 'UveVirtualNetworkConfig.total_acl_rules','operand2':{'json_value': '3'}}
        assert alarm_fix.set_alarm_rules([exp1,exp2,exp3]),'set alarm rules failed'
        sleep(15)
        self.logger.info('verify that the alarm does not gets raised when only few of the conditions met')
        assert not self.analytics_obj.verify_vn_acl_alarm(),'Alarm got raised'
        self.logger.info('Update alarm_config rules with multiple or conditions')
        assert alarm_fix.set_alarm_rules([exp1,exp2,exp3],multi_or_conditions=True),'set alarm rules failed'
        sleep(15)
        assert self.analytics_obj.verify_vn_acl_alarm(),'Alarm not raised'
        vn_pol_dict['vn_fixture'].unbind_policies(vn_pol_dict['vn_fixture'].vn_id)
        assert self.analytics_obj.verify_vn_acl_alarm(verify_alarm_cleared=True),'Alarm not cleared'
    #end verify_alarm_conf_with_multiple_rules

    def verify_alarm_scaling(self, parent_type='project'):
        exp1 = {'operation': '<=','operand1': "UveVirtualNetworkConfig.total_acl_rules",'operand2':{'json_value': '2'}}
        uve_keys = ['virtual-network']
        vn_pol_list=[]
        alarm_count=0
        if parent_type == 'global':
            alarm_fix = self.create_alarm([exp1],alarm_name,uve_keys,parent_type)
        for i in range(0,1000):
            alarm_name = 'vn_acl_rule'
            project_name = get_random_name('project')
            project_fixture = self.useFixture(
                        ProjectFixture(vnc_lib_h=self.vnc_lib,
                                       project_name=project_name,
                                       connections=self.connections))
            if parent_type == 'project':
                alarm_fix = self.create_alarm([exp1],alarm_name,uve_keys,parent_type,project_fixture)
                assert alarm_fix.verify_alarm_setup()
            vn_pol_dict=self.create_vn_policy_config(project_fixture,project_name)
            vn_pol_list.append(vn_pol_dict)
            ret=self.analytics_obj.verify_vn_acl_alarm()
            if ret:
                alarm_count=alarm_count+1
            else:
                assert ret,'Alarm not raised'
        self.logger.info('Total %s alarms got raised',alarm_count)
        for vn_pol_dict in vn_pol_list:
            vn_pol_dict['vn_fixture'].unbind_policies(vn_pol_dict['vn_fixture'].vn_id)
            ret = self.analytics_obj.verify_vn_acl_alarm(verify_alarm_cleared=True)
            if ret:
                alarm_count=alarm_count-1
            else:
                assert not ret,'Alarm not got cleared'
        self.logger.info('Total alarms left after clearing %s',alarm_count)
    #end verify_alarm_scaling

    def create_alarm(self,exp_list, alarm_name='test_alarm',uve_keys=[],parent_type='project',project_fixture=None ):
        alarm_fix = self.useFixture(AlarmFixture(
                    inputs=self.inputs,
                    connections=self.connections,
                    alarm_name=alarm_name,parent_obj_type = parent_type,
                    uve_keys=uve_keys,project_fixture=project_fixture))
        alarm_rules = alarm_fix.configure_alarm_rules(exp_list)
        alarm_fix.create(alarm_rules)
        self.logger.info('Alarm %s created successfully'%alarm_fix.alarm_name)
        return alarm_fix
    #end create_alarm

    def create_vn_policy_config(self,project_fixture=None,project_name=None):
        result =True
        vn_pol_dict={}
        vn_name = get_random_name('alarm_vn')
        vn_subnets = ['30.1.1.0/24']
        policy_name = get_random_name('policy')
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        vn_pol_dict['policy_fixture'] = self.useFixture(PolicyFixture(project_fixture=project_fixture,
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections,api='api'))
        policy_obj=vn_pol_dict['policy_fixture'].policy_obj
        vn_pol_dict['vn_fixture'] = self.useFixture(VNFixture(project_name=project_name,
                      project_obj=project_fixture,
                      connections=self.connections,
                      inputs=self.inputs,
                      vn_name=vn_name,
                      subnets=vn_subnets,
                      option='api',
                      policy_objs=[policy_obj]))
        return vn_pol_dict
    #end create_vn_policy_config
        