from common.vrouter.base import *
from builtins import str
from fabric.api import run
from tcutils.wrappers import preposttest_wrapper


class KernelCrashTest(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(KernelCrashTest, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(KernelCrashTest, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 2:
            return (False, 'Skipping Test. Need atleast two compute nodes')
        return (True, None)

    @preposttest_wrapper
    def test_crash_file_creation(self):
        '''
        Intentionally force a kernel crash on the first available compute node
        Validate that kernel crash file is created
        '''
        compute_ip = self.inputs.compute_ips[1]
        username = self.inputs.host_data[compute_ip]['username']
        password = self.inputs.host_data[compute_ip]['password']
        os_version = self.inputs.get_os_version(compute_ip)

        host_string='%s@%s' % (username, compute_ip)
        default_crash_file = '/var/crash'
        with settings(host_string=host_string, password=password, timeout=5):
            if os_version == 'ubuntu':
                cmd = 'kdump-config show | grep COREDIR | awk \'{print $2}\''
                crash_file = run(cmd)
                msg = 'Unable to determine crash file path using kdump-config'
                assert crash_file.succeeded, msg
            else:
                msg = ('/etc/kdump.conf not found! No kernel core file can get '
                    'created')
                assert exists('/etc/kdump.conf'), msg
                cmd = 'grep -o "^#path .*" kdump.conf | awk \'{print $2}\''
                crash_file = run(cmd) or default_crash_file

            files = str(run('ls %s' % (crash_file))).split()
            sudo('echo 1 > /proc/sys/kernel/sysrq')

            # Trigger panic
            try:
                sudo('echo c > /proc/sysrq-trigger')
                assert False, 'Kernel crash not triggered, failing the case'
            except CommandTimeout as e:
                self.logger.info('Kernel crash triggered, will wait for reboot')
        msg = 'Node %s not up after kernel crash' % (host_string)
        assert wait_for_ssh_on_node(host_string, password, self.logger), msg

        with settings(host_string='%s@%s' % (username, compute_ip),
                      password=password, timeout=5):
            later_files = str(run('ls %s ' % (crash_file))).split()
            msg = 'No new files found in %s' % (crash_file)
            assert len(later_files) > len(files), msg

            diff = set(later_files)-set(files)
            # Remove any newly created files
            for file_name in diff:
                run('rm -rf %s/%s' % (crash_file, file_name))
            self.logger.debug('Removed files %s' % (diff))
            self.logger.info('Kernel crash file created fine!')
    # end test_crash_file_creation

