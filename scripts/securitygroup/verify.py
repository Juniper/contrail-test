import os
import sys
from time import sleep

from util import retry
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.helpers import Host, Sender, Receiver
from traffic.core.profile import StandardProfile, ContinuousProfile


class VerifySecGroup():

    def verify_traffic(self, sender_vm, receiver_vm, proto, sport, dport, count=None, fip=None):
        # Create stream and profile
        if fip:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=fip)
        else:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=receiver_vm.vm_ip)
        profile_kwargs = {'stream': stream}
        if fip:
            profile_kwargs.update({'listener': receiver_vm.vm_ip})
        if count:
            profile_kwargs.update({'count': count})
            profile = StandardProfile(**profile_kwargs)
        else:
            profile = ContinuousProfile(**profile_kwargs)

        # Set VM credentials
        send_node = Host(sender_vm.vm_node_ip,
                         self.inputs.username, self.inputs.password)
        recv_node = Host(receiver_vm.vm_node_ip,
                         self.inputs.username, self.inputs.password)
        send_host = Host(sender_vm.local_ip,
                         sender_vm.vm_username, sender_vm.vm_password)
        recv_host = Host(receiver_vm.local_ip,
                         receiver_vm.vm_username, receiver_vm.vm_password)

        # Create send, receive helpers
        sender = Sender("send%s" %
                        proto, profile, send_node, send_host, self.inputs.logger)
        receiver = Receiver("recv%s" %
                            proto, profile, recv_node, recv_host, self.inputs.logger)

        # start traffic
        receiver.start()
        sender.start()
        sleep(5)

        # stop traffic
        sender.stop()
        receiver.stop()
        self.logger.info("Sent: %s; Received: %s", sender.sent, receiver.recv)
        return (sender.sent, receiver.recv)

    def assert_traffic(self, sender, receiver, proto, sport, dport,
                       expectation='pass'):
        self.logger.info("Sending %s traffic from %s with %s to %s with %s" %
                         (proto, sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1]))
        sent, recv = self.verify_traffic(sender[0], receiver[0],
                                         proto, sport, dport)
        if expectation == 'pass':
            msg = "%s traffic from %s with %s to %s with %s passed " % (proto,
                                                                        sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1])
            errmsg = "%s traffic from %s with %s to %s with %s Failed " % (proto,
                                                                           sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1])
            if (sent and recv == sent):
                self.logger.info(msg)
                return (True, msg)
            else:
                self.logger.error(errmsg)
                if self.inputs.stop_on_fail:
                    self.logger.info(
                        "Sub test failed; Stopping test for debugging.")
                    import pdb
                    pdb.set_trace()
                return (False, errmsg)

        elif expectation == 'fail':
            msg = "%s traffic from %s with %s to %s with %s "\
                "failed as expected" % (proto, sender[0].vm_name, sender[1],
                                        receiver[0].vm_name, receiver[1])
            errmsg = "%s traffic from %s with %s to %s with %s "\
                     "passed; Expcted to fail " % (proto, sender[0].vm_name, sender[1],
                                                   receiver[0].vm_name, receiver[1])
            if (recv == 0):
                self.logger.info(msg)
                return (True, msg)
            else:
                self.logger.error(errmsg)
                if self.inputs.stop_on_fail:
                    self.logger.info(
                        "Sub test failed; Stopping test for debugging.")
                    import pdb
                    pdb.set_trace()
                return (False, errmsg)

    def verify_sec_group_port_proto(self, port_test=False):
        results = []
        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg

    def verify_sec_group_with_udp_and_policy_with_tcp(self):
        results = []
        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg

    def verify_sec_group_with_udp_and_policy_with_tcp_port(self):
        results = []
        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))

        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg
