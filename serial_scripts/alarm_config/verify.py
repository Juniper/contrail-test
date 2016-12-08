from tcutils.util import *
from vn_test import *
from policy_test import *
from alarm_test import *


class VerifyAlarms():

    def verify_alarm_config(self, exp_list=[], update_list=[], parent_type='project', alarm_type='vn_acl_rule', uve_keys=['virtual-network'], alarm_case='basic'):
        self.parent_type = parent_type
        self.uve_keys = uve_keys
        alarm_name = get_random_name(alarm_type)
        alarm_fix = self.create_alarm(
            exp_list, alarm_name, self.uve_keys, parent_type=self.parent_type)
        assert alarm_fix.verify_alarm_setup()
        if alarm_type == 'vn_acl_rule':
            self.verify_vn_acl_alarm(
                alarm_fix, update_list, alarm_case, exp_list)

    def update_alarm_rules_and_verify(self, alarm_fix, update_list, multi_or_conditions=False):
        self.logger.info('Update alarm with new rules')
        assert alarm_fix.set_alarm_rules(
            update_list, multi_or_conditions), 'set alarm rules failed'
        assert alarm_fix.verify_alarm_setup()
        sleep(10)
        return self.analytics_obj.verify_configured_alarm(alarm_name=alarm_fix.alarm_name)

    def create_and_verify_vn_acl_config(self, alarm_name, project_fixture=None, project_name=None):
        vn_pol_dict = self.create_vn_policy_config(
            project_fixture, project_name)
        sleep(10)
        assert self.analytics_obj.verify_configured_alarm(
            alarm_name=alarm_name), 'Alarm not raised'
        return vn_pol_dict

    def delete_and_verify_vn_acl_config(self, vn_pol_dict):
        vn_pol_dict['vn_fixture'].unbind_policies(
            vn_pol_dict['vn_fixture'].vn_id)
        sleep(10)
        alarm_name = vn_pol_dict['alarm_fix'].alarm_name
        assert self.analytics_obj.verify_configured_alarm(
            alarm_name=alarm_name, verify_alarm_cleared=True), 'Alarm not cleared'

    def verify_vn_acl_alarm(self, alarm_fix, update_list, alarm_type, exp_list):
        if alarm_type == 'basic':
            vn_pol_dict = self.create_and_verify_vn_acl_config(
                alarm_fix.alarm_name)
            vn_pol_dict['alarm_fix'] = alarm_fix
            assert self.update_alarm_rules_and_verify(
                alarm_fix, update_list), 'Alarm not raised'
            self.delete_and_verify_vn_acl_config(vn_pol_dict)

        elif alarm_type == 'multi_condition':
            self.logger.info(
                'Created alarm_config rules with multiple And conditions')
            vn_pol_dict = self.create_and_verify_vn_acl_config(
                alarm_fix.alarm_name)
            vn_pol_dict['alarm_fix'] = alarm_fix
            self.logger.info('Update alarm with new And rules.'
                             ' Verify that the alarm does not gets raised when only few of the conditions met')
            assert not self.update_alarm_rules_and_verify(
                alarm_fix, update_list=update_list)
            self.logger.info(
                'Update alarm_config rules with multiple Or conditions')
            assert self.update_alarm_rules_and_verify(
                alarm_fix, update_list=update_list, multi_or_conditions=True), 'Alarm not raised'
            self.delete_and_verify_vn_acl_config(vn_pol_dict)

        elif alarm_type == 'invalid_cases':
            assert not alarm_fix.set_alarm_severity(
                '50'), 'Severity should not be allowed to set 50'
            assert not alarm_fix.set_alarm_rules(
                []), 'Empty alarm rules should not be allowed'
            assert not alarm_fix.set_uve_keys(
                ['invalid_key']), 'Invalid UVE keys should not be allowed'
            assert not alarm_fix.set_uve_keys(
                []), 'Empty UVE keys should not be allowed'
            assert not alarm_fix.set_alarm_rules(
                update_list), 'Invalid operation should not be allowed'

        elif alarm_type == 'scaling':
            alarm_count = 0
            vn_pol_list = []
            scaling_factor = 1000
            # if self.parent_type == 'global':
            #    alarm_fix = self.create_alarm(exp_list,alarm_name,uve_keys,parent_type=self.parent_type)
            for i in range(0, scaling_factor):
                alarm_name = get_random_name('vn_acl_rule')
                project_name = get_random_name('project')
                project_fixture = self.useFixture(
                    ProjectFixture(vnc_lib_h=self.vnc_lib,
                                   project_name=project_name,
                                   connections=self.connections))
                if self.parent_type == 'project':
                    alarm_fix = self.create_alarm(
                        exp_list, alarm_name, self.uve_keys, self.parent_type, project_fixture)
                    assert alarm_fix.verify_alarm_setup()
                vn_pol_dict = self.create_and_verify_vn_acl_config(
                    alarm_fix.alarm_name, project_fixture, project_name)
                vn_pol_dict['alarm_fix'] = alarm_fix
                vn_pol_list.append(vn_pol_dict)
                alarm_count = alarm_count + 1
            self.logger.info('Total %s alarms got raised', alarm_count)
            for vn_pol_dict in vn_pol_list:
                self.delete_and_verify_vn_acl_config(vn_pol_dict)
                alarm_count = alarm_count - 1
            self.logger.info(
                'Total alarms left after clearing %s', alarm_count)

    def create_alarm(self, exp_list, alarm_name='test_alarm', uve_keys=[], parent_type='project', project_fixture=None):
        alarm_fix = self.useFixture(AlarmFixture(
            inputs=self.inputs,
            connections=self.connections,
            alarm_name=alarm_name, parent_obj_type=parent_type,
            uve_keys=uve_keys, project_fixture=project_fixture))
        alarm_rules = alarm_fix.configure_alarm_rules(exp_list)
        alarm_fix.create(alarm_rules)
        self.logger.info('Alarm %s created successfully' %
                         alarm_fix.alarm_name)
        return alarm_fix

    def create_vn_policy_config(self, project_fixture=None, project_name=None):
        result = True
        vn_pol_dict = {}
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
                                                                      connections=self.connections, api='api'))
        policy_obj = vn_pol_dict['policy_fixture'].policy_obj
        vn_pol_dict['vn_fixture'] = self.useFixture(VNFixture(project_name=project_name,
                                                              project_obj=project_fixture,
                                                              connections=self.connections,
                                                              inputs=self.inputs,
                                                              vn_name=vn_name,
                                                              subnets=vn_subnets,
                                                              option='api',
                                                              policy_objs=[policy_obj]))
        return vn_pol_dict
