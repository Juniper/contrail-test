import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class StormControlProfileFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle storm control profile object
    Optional:
    :param name : name of the storm control profile
    :param uuid : UUID of the storm control profile
    :param action : one of 'shutdown'
    :param recovery_timeout : timeout in seconds to recover the interface from shutdown state
    :param bandwidth : value in int, when to raise the alarm (1-100)
    :param no_broadcast : 
    :param no_multicast : 
    :param no_unknown_unicast : 
    :param no_registered_multicast : 
    :param no_unregistered_multicast :
    '''
    def __init__(self, *args, **kwargs):
        super(StormControlProfileFixture, self).__init__(*args, **kwargs)
        self.name = kwargs.get('name') or get_random_name(self.project_name)
        self.uuid = kwargs.get('uuid')
        self.action = kwargs.get('action')
        self.recovery_timeout = kwargs.get('recovery_timeout')
        self.bandwidth = kwargs.get('bandwidth')
        self.no_broadcast = kwargs.get('no_broadcast') or False
        self.no_multicast = kwargs.get('no_multicast') or False
        self.no_unknown_unicast = kwargs.get('no_unknown_unicast') or False
        self.no_registered_multicast = kwargs.get('no_registered_multicast') or False
        self.no_unregistered_multicast = kwargs.get('no_unregistered_multicast') or False
        self.created = False
        self.verify_is_run = False
        self.fq_name = [self.domain, self.project_name, self.name]

    def setUp(self):
        super(StormControlProfileFixture, self).setUp()
        self.create()

    def cleanUp(self):
        if self.created == False and self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of storm control profile %s:'
                              %(self.fq_name))
        else:
            self.delete()
        super(StormControlProfileFixture, self).cleanUp()

    def get_object(self):
        return self.vnc_h.read_storm_control_profile(id=self.uuid)

    def read(self):
        obj = self.vnc_h.read_storm_control_profile(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        self.parent_type = obj.parent_type
        params = obj.get_storm_control_parameters()
        if params:
            self.action = params.get_action()
            self.recovery_timeout = params.get_recovery_timeout()
            self.bandwidth = params.get_bandwidth()
            self.no_broadcast = params.get_no_broadcast()
            self.no_multicast = params.get_no_multicast()
            self.no_unknown_unicast = params.get_no_unknown_unicast()
            self.no_registered_multicast = params.get_no_registered_multicast()
            self.no_unregistered_multicast = params.get_no_unregistered_multicast()

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.read_storm_control_profile(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.uuid = self.vnc_h.create_storm_control_profile(
                    fq_name=self.fq_name,
                    action=self.action,
                    recovery_timeout=self.recovery_timeout,
                    no_broadcast=self.no_broadcast,
                    no_multicast=self.no_multicast,
                    no_unknown_unicast=self.no_unknown_unicast,
                    no_registered_multicast=self.no_registered_multicast,
                    no_unregistered_multicast=self.no_unregistered_multicast,
                    bandwidth=self.bandwidth)
                self.created = True
                self.logger.info('Created Storm-control-profile %s(%s)'%(
                    self.name, self.uuid))
        if not self.created:
            self.read()

    def delete(self):
        self.logger.info('Deleting Storm Control Profile %s(%s)'%(self.name, self.uuid))
        try:
            self.vnc_h.delete_storm_control_profile(id=self.uuid)
        except NoIdError:
            pass

    def update(self, **kwargs):
        self.update_storm_control_profile(self.uuid, **kwargs)
        if 'action' in kwargs:
            self.action = kwargs['action']
        if 'recovery_timeout' in kwargs:
            self.recovery_timeout = kwargs['recovery_timeout']
        if 'bandwidth' in kwargs:
            self.bandwidth = kwargs['bandwidth']
        if 'no_broadcast' in kwargs:
            self.no_broadcast = kwargs['no_broadcast']
        if 'no_unknown_unicast' in kwargs:
            self.no_unknown_unicast = kwargs['no_unknown_unicast']
        if 'no_multicast' in kwargs:
            self.no_multicast = kwargs['no_multicast']
        if 'no_registered_multicast' in kwargs:
            self.no_registered_multicast = kwargs['no_registered_multicast']
        if 'no_unregistered_multicast' in kwargs:
            self.no_unregistered_multicast = kwargs['no_unregistered_multicast']

    def _compare_sc_retrieved(self, sc_dct, exp=True, model=None):
        mcast = False
        if exp != ((self.action or None) == sc_dct.get('action')):
            self.logger.debug('SC action didnt match, exp: %s, got %s'%(
                              self.action, sc_dct.get('action')))
            return False
        if exp != (int(self.bandwidth or 0) == int(sc_dct.get('bandwidth', 0))):
            self.logger.debug('SC bandwidth didnt match, exp: %s, got %s'%(
                              self.bandwidth, sc_dct.get('bandwidth')))
            return False
        if exp != (int(self.recovery_timeout or 0) ==
                   int(sc_dct.get('recovery_timeout', 0))):
            if self.action:
                self.logger.debug('SC recovery timeout didnt match, exp: %s, got %s'%(
                    self.recovery_timeout, sc_dct.get('recovery_timeout')))
                return False
        if self.no_broadcast != sc_dct.get('no_broadcast', False):
            if exp is True:
                self.logger.debug('SC no_broadcast didnt match, exp: %s, got %s'%(
                    self.no_broadcast, sc_dct.get('no_broadcast', False)))
                return False
        else:
            if self.no_broadcast is True and exp is False:
                self.logger.debug('SC no_broadcast didnt match, exp: %s, got %s'%(
                    self.no_broadcast, sc_dct.get('no_broadcast', False)))
                return False
        if self.no_unknown_unicast != sc_dct.get('no_unknown_unicast', False):
            if exp is True:
                self.logger.debug('SC no_unknown_unicast didnt match, exp: %s, got %s'%(
                    self.no_unknown_unicast, sc_dct.get('no_unknown_unicast', False)))
                return False
        else:
            if self.no_unknown_unicast is True and exp is False:
                self.logger.debug('SC no_unknown_unicast didnt match, exp: %s, got %s'%(
                    self.no_unknown_unicast, sc_dct.get('no_unknown_unicast', False)))
                return False
        if self.no_multicast != sc_dct.get('no_multicast', False):
            if exp is True:
                self.logger.debug('SC no_multicast didnt match, exp: %s, got %s'%(
                    self.no_multicast, sc_dct.get('no_multicast', False)))
                return False
        else:
            if self.no_multicast is True and exp is False:
                self.logger.debug('SC no_multicast didnt match, exp: %s, got %s'%(
                    self.no_multicast, sc_dct.get('no_multicast', False)))
                return False
        if model and model.startswith('qfx510'):
            return True
        if self.no_registered_multicast != sc_dct.get('no_registered_multicast', False):
            if exp is True:
                self.logger.debug('SC no_registered_multicast didnt match, exp: %s, got %s'%(
                    self.no_registered_multicast, sc_dct.get('no_registered_multicast', False)))
                return False
        else:
            if self.no_registered_multicast is True and exp is False:
                self.logger.debug('SC no_registered_multicast didnt match, exp: %s, got %s'%(
                    self.no_registered_multicast, sc_dct.get('no_registered_multicast', False)))
                return False
        if self.no_unregistered_multicast != sc_dct.get('no_unregistered_multicast', False):
            if exp is True:
                self.logger.debug('SC no_unregistered_multicast didnt match, exp: %s, got %s'%(
                    self.no_unregistered_multicast, sc_dct.get('no_unregistered_multicast', False)))
                return False
        else:
            if self.no_unregistered_multicast is True and exp is False:
                self.logger.debug('SC no_unregistered_multicast didnt match, exp: %s, got %s'%(
                    self.no_unregistered_multicast, sc_dct.get('no_unregistered_multicast', False)))
                return False
        return True

    @retry(tries=10, delay=6)
    def validate_config_pushed(self, prouters, interfaces, exp=True):
        for prouter in prouters:
            prouter_config = prouter.get_config()
            details = self.inputs.physical_routers_data[prouter.name]
            pr_interfaces = [interface['tor_port'].replace('_', ':')
                for interface in interfaces if interface['tor'] == prouter.name]
            intf = pr_interfaces[0]
            if len(interfaces) > 1:
                intfs = set()
                for interface in pr_interfaces:
                    intf = prouter.get_associated_ae_interface(interface,
                                                               prouter_config)
                    if len(intf) != 1:
                        self.logger.debug('Expect one ae intf associated to %s got %s'%(
                                   interface, intf or None))
                        return False
                    intfs.add(intf[0])
                if len(intfs) != 1:
                    return False, 'Expect one ae intf associated to %s got %s'%(
                                   pr_interfaces, intf or None)
                intf = list(intfs)[0]
            sc_config = prouter.get_storm_control_config(intf, prouter_config)
            if not self._compare_sc_retrieved(sc_config, exp, model=prouter.model):
                return False
        return True
