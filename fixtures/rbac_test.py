import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class RbacFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle Loadbalancer object
    Optional:
    :param name : name of the RBAC Acl
    :param uuid : UUID of the RBAC Acl
    :param parent_type : Parent type - one of project/domain/global-system-config (default: project)
    :param parent_fqname : fqname of the parent (default: derived from connections)
    :param rules : rbac rules 
                   eg: [{'rule_object': 'virtual_network',
                        'rule_field': 'route_target_list',
                        'perms': [{'role': 'admin', 'crud': 'CRUD'},
                                  {'role': '_member_', 'crud': 'R'}]
                        },
                        {'rule_object': '*',
                         'rule_field': '*',
                         'perms': [{'role': '*', 'crud': 'R'}]
                        }
                       ]
    '''
    def __init__(self, *args, **kwargs):
        super(RbacFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name') or 'default-api-access-list'
        self.uuid = kwargs.get('uuid')
        self.parent_type = kwargs.get('parent_type') or 'project'
        self.parent_fqname = kwargs.get('parent_fqname')
        self.rules = kwargs.get('rules') or list()
        self.created = False
        self.verify_is_run = False
        if not self.parent_fqname:
            if self.parent_type == 'project':
                self.parent_fqname = '%s:%s'%(self.domain, self.project_name)
            elif self.parent_type == 'domain':
                self.parent_fqname = self.domain
            else:
                self.parent_fqname = 'default-global-system-config'
        self.fq_name = '%s:%s'%(self.parent_fqname, self.name)
        if self.connections.inputs.verify_thru_gui():
            from webui_test import WebuiTest
            self.webui = WebuiTest(self.connections, self.inputs)

    def setUp(self):
        super(RbacFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(RbacFixture, self).cleanUp()
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of RBAC ACL %s :'
                              %(self.fq_name))
        else:
            if self.inputs.is_gui_based_config():
                self.webui.delete_rbac(self)
            else:
                return self.delete()

    def read(self):
        obj = self.vnc_h.get_api_access_list(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name_str()
        self.rules = list()
        entries = obj.get_api_access_list_entries()
        rules = entries.get_rbac_rule() if entries else []
        for rule in rules or []:
            perms = list()
            for perm in rule.get_rule_perms() or []:
                perms.append({'role': perm.get_role_name(),
                              'crud': perm.get_role_crud()})
            self.rules.append({'rule_object': rule.get_rule_object(),
                               'rule_field': rule.get_rule_field(),
                               'perms': perms})

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.get_api_access_list(fq_name_str=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                if self.inputs.is_gui_based_config():
                    self.webui.create_rbac(self)
                else:
                    self.uuid = self.vnc_h.create_api_access_list(
                                     parent_type=self.parent_type,
                                     fq_name=self.fq_name.split(':'),
                                     rules=self.rules)
                self.created = True
        if not self.inputs.is_gui_based_config():
            self.read()

    def add_rule(self, rule_object=None, rule_field=None, role='*', crud='CRUD'):
        rule = {'rule_object': rule_object,
                'rule_field': rule_field,
                'perms': [{'role': role, 'crud': crud}]
               }
        self.vnc_h.update_api_access_list(self.uuid, [rule])
        self.rules.extend([rule])

    def add_rules(self, rules):
        self.vnc_h.update_api_access_list(self.uuid, rules)
        self.rules.extend(rules)

    def delete_rule(self, rule_object=None, rule_field=None, role='*', crud='CRUD'):
        rule = {'rule_object': rule_object,
                'rule_field': rule_field,
                'perms': [{'role': role, 'crud': crud}]
               }
        self.vnc_h.update_api_access_list(self.uuid, [rule], delete=True)
        self.rules.remove(rule)

    def delete_rules(self, rules):
        self.vnc_h.update_api_access_list(self.uuid, rules, delete=True)
        for rule in rules:
            self.rules.remove(rule)

    def delete(self):
        self.vnc_h.delete_api_access_list(id=self.uuid)
        # ToDo: enable verify_is_run check when verify_on_cleanup becomes cumbersome
        assert self.verify_on_cleanup(), 'Rbac %s is still found in api server'%self.uuid

    def verify_on_setup(self):
        self.verify_is_run = True
        inspect_h = self.connections.api_server_inspect
        obj = inspect_h.get_api_access_list(self.uuid)
        if not obj:
            self.logger.error('API access-list (%s) not found in api server'%self.uuid)
            return False
        self.logger.debug('API access-list (%s) found in api server'%self.uuid)
        rules = obj.get_rules() or []
        if len(rules) != len(self.rules):
            self.logger.error('Rules doesnt match for API access-list (%s) '
                              'expected: %s, actual: %s'%(self.uuid,
                               self.rules, rules))
            return False
        # Compare Rules - ToDo: optimize lookup (currently n*n + m*m)
        for exp_rule in self.rules:
            for act_rule in rules:
                if exp_rule.get('rule_object') == act_rule['rule_object'] and \
                   exp_rule.get('rule_field') == act_rule['rule_field']:
                    for exp_perm in exp_rule['perms']:
                        for act_perm in act_rule['rule_perms']:
                            if exp_perm.get('role', '*') == act_perm['role_name'] and \
                               exp_perm.get('crud', 'CRUD') == act_perm['role_crud']:
                                break
                        else:
                            break
                    else:
                        break
            else:
                self.logger.error('Unable to find rule %s in actual_rules %s'%(exp_rule, rules))
                return False
        self.logger.info('API access-list %s verify on api server passed'%self.uuid)
        return True

    def verify_on_cleanup(self):
        inspect_h = self.connections.api_server_inspect
        obj = inspect_h.get_api_access_list(self.uuid)
        if obj:
            self.logger.error('API access-list (%s) found in api server after delete'%self.uuid)
            return False
        self.logger.info('API access-list (%s) got deleted in api server'%self.uuid)
        return True

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
    rbacfix = RbacFixture(connections=conn, rules=[{'rule_object': 'virtual_network',
                                                    'rule_field': 'route_target_list',
                                                    'perms': [{'role': 'admin', 'crud': 'CRUD'},
                                                              {'role': '_member_', 'crud': 'R'}]
                                                    },
                                                    {'rule_object': '*',
                                                     'rule_field': '*',
                                                     'perms': [{'role': '*', 'crud': 'R'}]
                                                    }
                                                   ])
    rbacfix.setUp()
    rbacfix.add_rule(rule_object='virtual_network', rule_field='route_target_list', role='Member', crud='R')
    rbacfix.verify_on_setup()
    rbacfix.add_rules([{'rule_object': None, 'rule_field': None, 'perms': [{'role': '*', 'crud': 'R'}]}])
    rbacfix.verify_on_setup()
    import pdb; pdb.set_trace()
    rbacfix.delete_rule(rule_object='virtual_network', rule_field='route_target_list', role='Member', crud='R')
    rbacfix.verify_on_setup()
    rbacfix.delete_rules([{'rule_object': None, 'rule_field': None, 'perms': [{'role': '*', 'crud': 'R'}]}])
    rbacfix.verify_on_setup()
    rbacfix.cleanUp()

if __name__ == "__main__":
    main()
