from builtins import str
import time
from tcutils.util import *
from common.contrail_fabric.base import BaseFabricTest
from common.device_connection import ConnectionFactory
from lxml.etree import XMLSyntaxError

class ZtpBaseTest(BaseFabricTest):
    ztp = True
    @classmethod
    def setUpClass(cls):
        super(ZtpBaseTest, cls).setUpClass()
        cls.netconf_sessions = dict()
        try:
            for device in list(cls.inputs.physical_routers_data.values()):
                cls.netconf_sessions[device['name']] = cls.get_connection_obj(
                    host=device['console'],
                    username=device['ssh_username'],
                    password=device['ssh_password'])
                filepath = '/tmp/'+str(device['name'])+'.conf'
                try:
                    cls.backup_config(device['name'], filepath=filepath)
                except XMLSyntaxError:
                    pass
                cls.zeroize_device(device['name'])
                cls.netconf_sessions[device['name']].disconnect()
        except:
            cls.tearDownClass()
        # Wait for zeroize (takes 10+ mins, onboard will wait for the rest)
        time.sleep(360)
    #end setUpClass

    @staticmethod
    def get_connection_obj(host, username, password):
        conn_obj = ConnectionFactory.get_connection_obj(
            'juniper', host=host, username=username,
            password=password, mode='telnet')
        conn_obj.connect()
        return conn_obj
    # end get_connection_obj

    @classmethod
    def zeroize_device(cls, device_name):
        cls.netconf_sessions[device_name].zeroize()

    @classmethod
    def backup_config(cls, device_name, filepath):
        with open(filepath, 'w') as fd:
            fd.write(cls.netconf_sessions[device_name].get_config(mode='text'))

    @classmethod
    def restore_config(cls, device_name, filepath):
        try:
            cls.netconf_sessions[device_name].config(path=filepath, overwrite=True,
                                                     merge=False, timeout=60)
        except XMLSyntaxError:
            pass

    @classmethod
    def tearDownClass(cls):
        super(ZtpBaseTest, cls).tearDownClass()
        for device in list(cls.inputs.physical_routers_data.values()):
            filepath = '/tmp/'+str(device['name'])+'.conf'
            cls.netconf_sessions[device['name']] = cls.get_connection_obj(
                host=device['console'],
                username=device['ssh_username'],
                password=device['ssh_password'])
            try:
                cls.restore_config(device['name'], filepath=filepath)
            finally:
                cls.netconf_sessions[device['name']].disconnect()
    #end tearDownClass
