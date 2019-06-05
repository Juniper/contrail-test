import time

from telnetlib import Telnet
from tcutils.util import *
from common.contrail_fabric.base import BaseFabricTest
from common.contrail_fabric.base import FabricSingleton

#import test_v1

class ZtpBaseTest(BaseFabricTest):

    @classmethod
    def setUpClass(cls, inputs=None):
        super(ZtpBaseTest, cls).setUpClass()
        for device in [device for device in cls.inputs.physical_routers_data.values()]:
            file_path = '/tmp/'+str(device['name'])+'.conf'
            cls.backup_config(
                host=device['telnet_console'],
                username=device['ssh_username'],
                password=device['ssh_password'],
                filepath=file_path)
            cls.zeroize_device(
                host=device['telnet_console'],
                username=device['ssh_username'],
                password=device['ssh_password'])
        cls.ztp = True
    #end setUpClass

    @classmethod
    def zeroize_device(cls, host, username='root', password='c0ntrail123',
        port=23, timeout=10):
        return execute_zeroize(
            host=host,
            username=username,
            password=password,
            timeout=timeout)

    @classmethod
    def backup_config(cls, host, filepath, username='root', password='c0ntrail123',
        port=23, timeout=60):
        return execute_backup_config(
            host=host,
            username=username,
            password=password,
            filepath=filepath,
            timeout=timeout)

    @classmethod
    def restore_config(cls, host, filepath, username='root', password='c0ntrail123',
        port=23, timeout=60):
        return execute_restore_config(
            host=host,
            username=username,
            password=password,
            filepath=filepath,
            timeout=timeout)

    @classmethod
    def tearDownClass(cls):
        super(ZtpBaseTest, cls).tearDownClass()
        for device in [device for device in cls.inputs.physical_routers_data.values()]:
            cls.restore_config(
                host=device['telnet_console'],
                username=device['ssh_username'],
                password=device['ssh_password'],
                filepath=device['backup_config_file_path'])
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        self.remove_api_from_cleanups(fix.cleanUp)
   #end remove_from_cleanups

    def remove_api_from_cleanups(self, api):
        for cleanup in self._cleanups:
            if api in cleanup:
                self._cleanups.remove(cleanup)
                break
   #end remove_api_from_cleanups


