import fixtures
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from time import sleep
from contrail_fixtures import *
import inspect
from tcutils.config import vnc_api_results
from contrailapi import ContrailVncApi


class AlarmFixture(fixtures.Fixture):

    ''' Fixture to create and verify and delete alarms.
        Create AlarmFixture object
    '''

    def __init__(self, connections, alarm_name=None, uve_keys=[], alarm_severity=None,
                 alarm_rules=None, operand1=None, operand2=None, description=None, variables=None,
                 id_perms=None, perms2=None, display_name=None, parent_obj_type='project',
                 clean_up=True, project_name=None, project_fixture=None):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.connections.logger
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.vnc_h = ContrailVncApi(self.vnc_lib_h, self.logger)
        self.api_s_inspect = self.connections.api_server_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.alarm_name = alarm_name
        self.alarm_id = None
        self.alarm_fq_name = [self.inputs.domain_name, self.alarm_name]
        self.uve_keys = uve_keys
        self.alarm_severity = alarm_severity
        self.alarm_rules = alarm_rules
        self.operand1 = operand1
        self.operand2 = operand2
        self.description = description
        self.variables = variables
        self.id_perms = id_perms
        self.perms2 = perms2
        self.display_name = display_name
        self.parent_obj_type = parent_obj_type
        self.domain_name = self.connections.domain_name
        self.project_name = project_name or self.connections.project_name
        self.project_fixture = project_fixture
        if self.project_fixture:
            self.project_name = self.project_fixture.project_name
        self.project_id = self.connections.get_project_id()
        self.parent_obj = None
        self.clean_up = clean_up
        self.obj = None
        self.created = False
    # end __init__

    def read(self):
        if self.alarm_id:
            self.alarm_obj = self.vnc_h.get_alarm(self.alarm_id)
            self.alarm_fq_name = self.get_fq_name()
            self.alarm_name = self.alarm_obj.name
    # end read

    def setUp(self):
        super(AlarmFixture, self).setUp()
    # end setup

    def create(self, alarm_rules):
        self.alarm_rules = alarm_rules
        self.alarm_id = self.alarm_id or self.get_alarm_id()
        if self.alarm_id:
            self.read()
            self.logger.debug("alarm already present not creating" %
                              (self.alarm_name, self.alarm_id))
        else:
            self.logger.debug(" creating alarm : %s", self.alarm_name)
            if self.parent_obj_type == 'global':
                self.parent_obj = self.vnc_h.get_global_config_obj()
            if self.parent_obj_type == 'project':
                if not self.project_fixture:
                    self.project_fixture = self.useFixture(
                        ProjectFixture(project_name=self.project_name,
                                       connections=self.connections))
                self.parent_obj = self.project_fixture.getObj()
            if not self.parent_obj:
                raise AmbiguousParentError(
                    "[[u'default-global-system-config'], [u'default-domain', u'default-project']]")
            if not self.alarm_rules:
                self.alarm_rules = self.create_alarm_rules()
            uve_keys_type = UveKeysType(self.uve_keys)
            self.alarm_id = self.vnc_h.create_alarm(name=self.alarm_name, parent_obj=self.parent_obj,
                                   alarm_rules=self.alarm_rules, alarm_severity=self.alarm_severity,
                                   uve_keys=uve_keys_type)
            # need to set rules and other parameters before passing alarm_obj
            self.alarm_obj = self.vnc_h.get_alarm(self.alarm_id)
            self.alarm_fq_name = self.get_fq_name()
            self.created = True
    # end create

    def create_expression(self, params_dict):
        return AlarmExpression(params_dict=params_dict)
    # end create_expression

    def create_and_list(self, and_list):
        return AlarmAndList(and_list=and_list)
    # end create_and_list

    def create_or_list(self, or_list):
        return AlarmOrList(or_list=or_list)
    # end create_or_list

    def configure_alarm_rules(self, params_dict_list, multi_or_conditions=False):
        '''configure single or multiple rules'''
        self.alarm_exp_list = []
        self.alarm_and_list = []
        self.alarm_or_list = []
        try:
            for params_dict in params_dict_list:
                alarm_exp = self.create_expression(params_dict)
                self.alarm_exp_list.append(alarm_exp)
            if multi_or_conditions:
                for alarm_exp in self.alarm_exp_list:
                    alarm_and = self.create_and_list([alarm_exp])
                    self.alarm_and_list.append(alarm_and)
            else:
                self.alarm_and_list.append(
                    self.create_and_list(self.alarm_exp_list))
            self.alarm_or_list = self.create_or_list(self.alarm_and_list)
            return self.alarm_or_list
        except:
            self.logger.warn('error configuring alarm')
    # end configure_alarm_rules

    def getObj(self):
        return self.alarm_obj
    # end getObj

    def set_display_name(self, display_name):
        self.display_name = display_name
        self.alarm_obj.set_display_name(display_name)
        self.vnc_h.update_alarm(self.alarm_obj)
    # end set_display_name

    def get_display_name(self):
        return self.alarm_obj.get_display_name()
    # end get_display_name

    def get_alarm_id(self):
        if not self.alarm_id:
            try:
                alarm_obj = self.vnc_h.get_alarm(self.alarm_fq_name)
                if alarm_obj:
                    self.alarm_id = alarm_obj.uuid
                    return self.alarm_id
            except:
                return None
    # end get_alarm_id


    def set_alarm_rules(self, exp_list, multi_or_conditions=False):
        rules = self.configure_alarm_rules(
            exp_list, multi_or_conditions=multi_or_conditions)
        try:
            if rules:
                self.alarm_obj.set_alarm_rules(rules)
                self.vnc_h.update_alarm(self.alarm_obj)
                return True
        except:
            self.logger.warn('Setting alarm_rules Failed')
            return None
    # end set_alarm_rules

    def set_alarm_enable(self, enable):
        pass

    def set_alarm_disable(self):
        pass

    def get_alarm_severity(self):
        return self.alarm_severity
    # end get_alarm_severity

    def set_alarm_severity(self, severity):
        try:
            self.alarm_severity = severity
            self.alarm_obj.set_alarm_severity(severity)
            self.vnc_h.update_alarm(self.alarm_obj)
            return True
        except :
            self.logger.warn('Setting alarm Severity Failed')
            return None
    # set_alarm_severity

    def set_uve_keys(self, uve_key):
        try:
            self.uve_keys = uve_key
            uve_key_type = UveKeysType(uve_key)
            self.alarm_obj.set_uve_keys(uve_key_type)
            self.vnc_h.update_alarm(self.alarm_obj)
            return True
        except :
            self.logger.warn('Setting UVE keys Failed')
            return None
    # set_uve_keys

    def get_uve_keys(self):
        return self.uve_keys
    # end get_uve_keys
    
    def get_fq_name(self):
        obj = self.getObj()
        fq_name = obj.get_fq_name()
        return ':'.join(fq_name)

    def verify_alarm_in_api_server(self):
        self.cs_alarm = self.api_s_inspect.get_cs_alarm(
                alarm_id=self.alarm_id)
        if not self.cs_alarm:
            self.logger.warn(
                'Alarm config of %s not present in api server' % self.alarm_name)
            return False
        self.logger.info(
            'Alarm config of %s present in the api-server' % self.alarm_name)
        return True
    # end verify_alarm_in_api_server

    def verify_alarm_configuration(self):
        alarm_config = self.cs_alarm
        alarm = alarm_config.get('alarm')
        name = alarm.get('display_name')
        if not (name == self.alarm_name):
            self.logger.warn('Alarm name is missing in the config')
            return False
        uve_keys_dict = alarm.get('uve_keys')
        uve_keys = uve_keys_dict.get('uve_key')
        if not (uve_keys == self.uve_keys):
            self.logger.warn('Uve_keys not present or doesn\'t match %s %s' % (
                uve_keys, self.uve_keys))
            return False
        rules = alarm.get('alarm_rules')
        if not rules:
            self.logger.warn('Rules are not present in config')
            return False
        self.logger.info('Alarm %s configured properly ' %self.alarm_name)
        return True
    # end verify_alarm_configuration

    @retry(delay=3, tries=10)
    def verify_alarm_not_in_api_server(self):
        cs_alarm = self.api_s_inspect.get_cs_alarm(
            alarm_id=self.alarm_id)
        if cs_alarm:
            errmsg = 'Alarm %s not removed from api-server' % self.alarm_name
            self.logger.warn(errmsg)
            return False
        self.logger.info('Alarm %s removed from api-server' % self.alarm_name)
        return True
    # end verify_alarm_not_in_api_server

    def verify_on_setup(self):
        '''Verify alarm in configuration '''
        result = True
        result = self.verify_alarm_in_api_server()
        if not result:
            self.logger.error(
                'Verification of %s config in api-server failed' % self.alarm_name)
            return result
        result = self.verify_alarm_configuration()
        if not result:
            self.logger.error('Alarm %s not configured properly' %self.alarm_name)
            return result
        return True
    # end verify_alarm_setup

    def cleanUp(self):
        super(AlarmFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if not self.created:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if self.clean_up == False:
            do_cleanup = False
        if do_cleanup:
            self._delete_alarm()
            self.logger.info('Deleted alarm %s' % self.alarm_name)
            assert self.verify_alarm_not_in_api_server()
        else:
            self.logger.debug('Skippping deletion of alarm %s' %
                              self.alarm_name)
    # end cleanup

    def _delete_alarm(self, verify=False):
        self.vnc_h.delete_alarm(self.alarm_id)
    # end _delete_alarm
