import os
import sys
import errno
import subprocess
import time
import argparse

from vnc_api.vnc_api import *
import vnc_api
from svc_monitor import svc_monitor
#from svc_monitor.common import network as common_nw_client


class PolicyCmd(object):

    def __init__(self, args_str=None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        self._domain_fq_name = [self._args.domain_name]
        self._proj_fq_name = [self._args.domain_name, self._args.proj_name]
        self._policy_fq_name = [self._args.domain_name,
                                self._args.proj_name, self._args.policy_name]

        self._vn_fq_list = [[self._args.domain_name, self._args.proj_name, vn]
                            for vn in self._args.vn_list or []]
        #self._svc_list = [":".join(self._proj_fq_name) + ':' + s for s in self._args.svc_list or []]

        self._vnc_lib = VncApi('u', 'p',
                               api_server_host=self._args.api_server_ip,
                               api_server_port=self._args.api_server_port)

    # end __init__

    def _parse_args(self, args_str):
        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'domain_name': 'default-domain',
            'proj_name': 'demo',
            #'svc_list'        : None,
            'vn_list': None,
            'api_server_ip': '127.0.0.1',
            'api_server_port': '8082',
        }

        args.conf_file = '/etc/contrail/svc_monitor.conf'
        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            global_defaults.update(dict(config.items("DEFAULTS")))

        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        parser = argparse.ArgumentParser(
            # Inherit options from config_parser
            parents=[conf_parser],
            # print script description with -h/--help
            description=__doc__,
            # Don't mess with format of description
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.set_defaults(**global_defaults)
        subparsers = parser.add_subparsers()

        create_parser = subparsers.add_parser('add')
        create_parser.add_argument("policy_name", help="service policy name")
        #create_parser.add_argument("--svc_list", help = "service instance name(s)", nargs='+', required=True)
        create_parser.add_argument(
            "--vn_list", help="ordered list of VNs", nargs=2, required=True)
        create_parser.add_argument(
            "--proj_name", help="name of project [default: demo]")
        create_parser.set_defaults(func=self.create_policy)

        delete_parser = subparsers.add_parser('del')
        delete_parser.add_argument("policy_name", help="service policy name")
        delete_parser.add_argument(
            "--proj_name", help="name of project [default: demo]")
        delete_parser.set_defaults(func=self.delete_policy)

        self._args = parser.parse_args(remaining_argv)
    # end _parse_args

    def create_policy(self):
        if self._vn_fq_list == []:
            print "Error: VN list or Service list is empty"
            return

        mirror = None
        policy_flag = 'transparent'

        print "Create and attach policy %s" % (self._args.policy_name)
        project = self._vnc_lib.project_read(fq_name=self._proj_fq_name)
        try:
            vn_obj_list = [self._vnc_lib.virtual_network_read(vn)
                           for vn in self._vn_fq_list]
        except NoIdError:
            print "Error: VN(s) %s not found" % (self._args.vn_list)
            return

        addr_list = [AddressType(virtual_network=vn.get_fq_name_str())
                     for vn in vn_obj_list]

        port = PortType(0, -1)
        action_list = None
        action = "pass"
        timer = None

        if mirror:
            mirror_action = MirrorActionType(mirror)
            action_list = ActionListType(mirror_to=mirror_action)
            action = None
            timer = TimerType()

        port = PortType(0, -1)
        prule = PolicyRuleType(direction="<>", simple_action=action,
                               protocol="any", src_addresses=[addr_list[0]],
                               dst_addresses=[addr_list[1]], src_ports=[port],
                               dst_ports=[port], action_list=action_list)

        # ran but did not add 2 targets
        # prule = PolicyRuleType(direction="<>", simple_action=action,
        #                   protocol="any", src_addresses=[addr_list[0]],
        #                   dst_addresses=[addr_list[1]], action_list=action_list)
        # prule = PolicyRuleType(direction="<>", simple_action=action,
        #                   protocol="any", src_addresses=[addr_list[0]],
        #                   dst_addresses=[addr_list[1]], src_ports=None,
        #                   dst_ports=None, action_list=action_list)

        pentry = PolicyEntriesType([prule])
        np = NetworkPolicy(
            name=self._args.policy_name, network_policy_entries=pentry,
            parent_obj=project)
        self._vnc_lib.network_policy_create(np)

        seq = SequenceType(1, 1)
        vn_policy = VirtualNetworkPolicyType(seq, timer)
        for vn in vn_obj_list:
            vn.set_network_policy(np, vn_policy)
            self._vnc_lib.virtual_network_update(vn)

        return np
    # end create_policy

    def delete_policy(self):
        print "Deleting policy %s" % (self._args.policy_name)
        try:
            np = self._vnc_lib.network_policy_read(self._policy_fq_name)
        except NoIdError:
            print "Error: Policy %s not found for delete" % (self._args.policy_name)
            return

        for network in (np.get_virtual_network_back_refs() or []):
            try:
                vn_obj = self._vnc_lib.virtual_network_read(
                    id=network['uuid'])
                for name in vn_obj.network_policy_refs:
                    if self._policy_fq_name == name['to']:
                        vn_obj.del_network_policy(np)
                        self._vnc_lib.virtual_network_update(vn_obj)
            except NoIdError:
                print "Error: VN %s not found for delete" % (network['to'])

        self._vnc_lib.network_policy_delete(fq_name=self._policy_fq_name)
    # delete_policy

# end class ServicePolicyCmd


def main(args_str=None):
    sp = PolicyCmd(args_str)
    sp._args.func()
# end main

if __name__ == "__main__":
    main()
