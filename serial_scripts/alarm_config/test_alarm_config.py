import fixtures
from tcutils.wrappers import preposttest_wrapper
from alarm_config.base import *
from alarm_test import *
from verify import VerifyAlarms


class TestAlarmConfigCases(BaseAlarmConfigTest,VerifyAlarms):

    @classmethod
    def setUpClass(cls):
        super(TestAlarmConfigCases, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    def test_alarm_conf_in_global_config(self):
        '''
        1. Configure an alarm with condition 'UveVirtualNetworkConfig.total_acl_rules <= 2''
        2. Verify the configuration under global system config
        3. Configure vn, add policy rules
        4. Verify that the configured alarm gets raised for the same
        5. Clear the configuration and verify that alarm got cleared
        6. Update the alarm with new rules and verify alarm got updated
        7. Verify alarm got raised for new condition
        8. Clear the configuration and verify that alarm got cleared
        '''
        self.verify_alarm_config(parent_type='global')

    # end test_alarm_conf_in_global_config

    def test_alarm_conf_in_project(self):
        '''
        1. Configure an alarm with condition 'UveVirtualNetworkConfig.total_acl_rules <= 2'
        2. Verify the configuration under project
        3. Configure vn, add policy rules
        3. Configure vn, add policy rules
        4. Verify that the configured alarm gets raised for the same
        5. Clear the configuration and verify that alarm got cleared
        6. Update the alarm with new rules and verify alarm got updated
        7. Verify alarm got raised for new condition
        8. Clear the configuration and verify that alarm got cleared
        '''
        self.verify_alarm_config()

    #end test_alarm_conf_in_project
     
    def test_alarm_conf_with_multiple_rules_in_global_config(self):
        '''
        1. Configure an alarm with  and conditions 'UveVirtualNetworkConfig.total_acl_rules <= 2'
           and UveVirtualNetworkConfig.total_acl_rules <= 1 and UveVirtualNetworkConfig.total_acl_rules == 1
        2. Verify the configuration under global_config
        3. Configure vn, add policy rules
        4. Verify that the alarm got raised
        5. Update the alarm with new And rules
        6. Verify alarm does not gets raised when only one of the conditions met
        7. update the alarm with new OR rules
        8. verify alarm gets raised for new condition
        9. clear the configuration and verify that alarm gets cleared
        '''
        self.verify_alarm_conf_with_multiple_rules(parent_type='global')

    #end test_alarm_conf_with_multiple_rules_in_global_config

    def test_alarm_conf_with_multiple_rules_in_project(self):
        '''
        1. Configure an alarm with  multiple AND conditions
        2. Verify the configuration under project
        3. Configure vn, add policy rules
        4. Verify that the alarm got raised
        5. Update the alarm with new And rules
        6. Verify alarm does not gets raised when only one of the conditions met
        7. update the alarm with new OR rules
        8. verify alarm gets raised for new condition
        9. clear the configuration and verify that alarm gets cleared
        '''
        self.verify_alarm_conf_with_multiple_rules(parent_type='project')

    #end test_alarm_conf_with_multiple_rules_in_project
    
    def test_alarm_conf_with_invalid_cases_in_global_config(self):
        '''
        1. Configure alarm with invalid severity = 50 and should not be allowed
        2. Confiure alarm with empty rule . Alarm with empty rule should not get raised
        3. Configure alarm with invalid UVE keys list Configuration should not be allowed
        4. Configure alarm with empty UVE keys list Configuration should not be allowed
        5. Configure alarm rule with invalid operators/operands Configuration should not be allowed
        6. Try updating field of any in-built alarm Updating in-built alarm should not be allowed
        '''
        self.verify_conf_with_invalid_cases(parent_type='global')

    #end test_alarm_conf_with_invalid_cases_in_global_config
    
    def test_alarm_conf_with_invalid_cases_in_projects(self):
        '''
        1. Configure alarm with invalid severity = 50 and should not be allowed
        2. Confiure alarm with empty rule . Alarm with empty rule should not get raised
        3. Configure alarm with invalid UVE keys list Configuration should not be allowed
        4. Configure alarm with empty UVE keys list Configuration should not be allowed
        5. Configure alarm rule with invalid operators/operands Configuration should not be allowed
        6. Try updating field of any in-built alarm Updating in-built alarm should not be allowed
        '''
        self.verify_conf_with_invalid_cases(parent_type='project')

    #end test_alarm_conf_with_invalid_cases_in_projects

    def test_alarm_scaling_under_global_config(self):
        '''
        1. Create an alarm on global config
        2. Try Creating 100 projects
        3. Configure vn and policy rules on each project
        4. Verify alarms are being generated for each project
        5. Delete the policies on every vn and verify alarms cleared
        '''
        self.verify_alarm_scaling(parent_type='global')

    #end test_alarm_scaling_under_global_config

    def test_alarm_scaling_under_project(self):
        '''
        1. Try Creating 100 projects
        2. Create an alarm on each project
        3. Configure vn and policy rules on each project
        4. Verify alarms are being generated for each project
        5. Delete the policies on every vn and verify alarms cleared
        '''
        self.verify_alarm_scaling()

    #end test_alarm_scaling_under_project

    #def test_alarm_conf_with_multiple_projects(self):
    #    self.verify_alarm_conf_with_multiple_projects()
