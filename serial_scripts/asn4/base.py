import test_v1
from common.device_connection import NetconfConnection, SSHConnection


class ASN4Base(test_v1.BaseTestCase_v1):

    AS_TRANS = 23456
    AS_2BYTE_MAX = 65535

    def vsrx1_addnl_static_routes(self):
        static_routes = ["41.41.41.0/24", "42.42.42.0/24"]
        return static_routes

    def vsrx1_aggr_routes(self):
        static_routes = ["47.47.1.0/24", "47.47.2.0/24"]
        aggr_route = "47.47.0.0/16"
        return aggr_route, static_routes

    def vsrx2_addnl_static_routes(self):
        static_routes = ["45.45.45.0/24", "46.46.46.0/24"]
        return static_routes

    def vsrx2_aggr_routes(self):
        static_routes = ["48.48.1.0/24", "48.48.2.0/24"]
        aggr_route = "48.48.0.0/16"
        return aggr_route, static_routes

    def get_mx_configured_addnl_static_routes(self):
        mx_static_routes = ["22.22.22.22/32", "33.33.33.33/32"]
        return mx_static_routes

    def get_external_mx_configured_addnl_static_routes(self):
        mx_static_routes = ["71.71.71.71/32"]
        return mx_static_routes

    def get_mx_configured_aggr_routes(self):
        mx_static_routes = ["44.44.44.1/32", "44.44.44.2/32", "44.44.44.3/32"]
        mx_aggr_route = "44.44.0.0/16"
        return mx_aggr_route, mx_static_routes

    def get_external_mx_configured_aggr_routes(self):
        mx_static_routes = ["7.7.7.7/32", "7.7.7.8/32"]
        mx_aggr_route = "7.7.0.0/16"
        return mx_aggr_route, mx_static_routes

    @classmethod
    def setUpClass(cls):
        super(ASN4Base, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def mx_static_routes_configuration(self, control_node_config, mx_config, vn_fixture):
        static_routes = self.get_mx_configured_addnl_static_routes()
        self.logger.info("Create static route configuration in MX")
        test_group_name = mx_config['test_group_name']
        test_bgp_proto_group_name = mx_config['test_bgp_proto_group_name']
        ri_name = mx_config["ri_name"]
        vrf_target = self.get_vrf_target(control_node_config, vn_fixture)
        cmds = []
        cmds.append(
            "set groups %s policy-options policy-statement get_static_routes from protocol static" % test_group_name)
        for static_route in static_routes:
            cmds.append("set groups %s routing-instances %s routing-options static route %s discard" %
                        (test_group_name, ri_name, static_route))
            cmds.append("set groups %s policy-options policy-statement get_static_routes from route-filter %s exact" %
                        (test_group_name, static_route))
        cmds.append(
            "set groups %s policy-options policy-statement get_static_routes then community add 2byte" % test_group_name)
        cmds.append(
            "set groups %s policy-options policy-statement get_static_routes then accept" % test_group_name)
        cmds.append("set groups %s routing-instances %s vrf-export get_static_routes " %
                    (test_group_name, ri_name))
        cleanup_cmds = []
        self.provision_mx(mx_config['control_ip'], cmds, cleanup_cmds)

    def mx_aggregated_routes_configuration(self, control_node_config, mx_config, vn_fixture):
        aggr_route, static_routes = self.get_mx_configured_aggr_routes()
        self.logger.info("Create aggregated routes configuration in MX")
        test_group_name = mx_config['test_group_name']
        ri_name = mx_config["ri_name"]

        vrf_target = self.get_vrf_target(control_node_config, vn_fixture)
        cmds = []
        cmds.append("set groups %s routing-instances %s routing-options aggregate route %s policy get_routes" %
                    (test_group_name, ri_name, aggr_route))
        cmds.append(
            "set groups %s policy-options policy-statement get_routes from protocol static" % test_group_name)
        for static_route in static_routes:
            cmds.append("set groups %s routing-instances %s routing-options static route %s discard" %
                        (test_group_name, ri_name, static_route))
            cmds.append("set groups %s policy-options policy-statement get_routes from route-filter %s exact" %
                        (test_group_name, static_route))
        cmds.append(
            "set groups %s policy-options policy-statement get_routes then accept" % test_group_name)
        cmds.append(
            "set groups %s policy-options policy-statement export_aggr from protocol aggregate" % test_group_name)
        cmds.append(
            "set groups %s policy-options policy-statement export_aggr then community add 2byte" % test_group_name)
        cmds.append(
            "set groups %s policy-options policy-statement export_aggr then accept" % test_group_name)
        cmds.append("set groups %s policy-options community 2byte members %s" %
                    (test_group_name, vrf_target))
        cmds.append("set groups %s routing-instances %s vrf-export export_aggr " %
                    (test_group_name, ri_name))

        cleanup_cmds = []
        self.provision_mx(mx_config['control_ip'], cmds, cleanup_cmds)

    def add_vrf_target(self, control_node_config, vn_fixture, vrf_target):
        target, router_asn, route_target_number = vrf_target.split(":")
        vn_fixture.add_route_target(routing_instance_name=vn_fixture.ri_name,
                                    router_asn=router_asn, route_target_number=route_target_number)

    def get_vrf_target(self, control_node_config, vn_fixture):
        vn_obj = self.connections.vnc_lib.virtual_network_read(
            id=vn_fixture.vn_id)
        ri_uuid = vn_obj.get_routing_instances()[0]['uuid']
        ri = self.connections.vnc_lib.routing_instance_read(id=ri_uuid)
        rt = ri.route_target_refs[0]['to'][0].split(":")
        cluster_global_asn = control_node_config['cluster_global_asn']
        if int(cluster_global_asn) < self.AS_2BYTE_MAX:
            vrf_target = "target:%s:%s" % (cluster_global_asn, rt[2])
        else:
            vrf_target = "target:%sL:%s" % (cluster_global_asn, rt[2])
        return vrf_target

    def external_route_config(self, mx_router_params, ext_mx_router_params, vrf_target):

        configs = [(mx_router_params, ext_mx_router_params),
                   (ext_mx_router_params, mx_router_params)]
        for router_params, router_params2 in configs:
            if router_params['mx_asn'] == router_params2['mx_asn']:
                peer_type = "internal"
            else:
                peer_type = "external"

            cmds1 = []
            cmds1.append("delete groups %s" % router_params['test_group_name'])
            cmds1.append("delete apply-groups %s" %
                         router_params['test_group_name'])
            cleanup_cmds = []
            self.provision_mx(
                router_params['mgmt_ip'], cmds1, cleanup_cmds, ignore_errors=True)

            test_group_name = router_params['test_group_name']
            test_bgp_proto_group_name = router_params['test_bgp_proto_group_name']
            peer_addr = router_params2['loopback_ip']
            cmds1 = []
            cmds1.append("set groups %s routing-options autonomous-system %s" %
                         (test_group_name, router_params['mx_asn']))
            cmds1.append("set groups %s protocols bgp group %s type %s" % (
                test_group_name, test_bgp_proto_group_name, peer_type))
            cmds1.append("set groups %s protocols bgp group %s traceoptions file %s_log" % (
                test_group_name, test_bgp_proto_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s traceoptions file size 4294967295" % (
                test_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s traceoptions file world-readable" %
                         (test_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s family inet unicast" % (
                test_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s family inet-vpn unicast" %
                         (test_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s family route-target" %
                         (test_group_name, test_bgp_proto_group_name))
            cmds1.append("set groups %s protocols bgp group %s local-as %s" %
                         (test_group_name, test_bgp_proto_group_name, router_params['mx_asn']))
            cmds1.append("set groups %s protocols bgp group %s local-address %s" %
                         (test_group_name, test_bgp_proto_group_name, router_params['loopback_ip']))
            cmds1.append("set groups %s protocols bgp group %s neighbor %s" % (
                test_group_name, test_bgp_proto_group_name, peer_addr))
            cmds1.append("set groups %s protocols bgp group %s multihop" %
                         (test_group_name, test_bgp_proto_group_name))

            peer_asn = router_params2['mx_asn']
            if not router_params['mx_4b_capability']:
                cmds1.append("set groups %s protocols bgp group %s disable-4byte-as" %
                             (test_group_name, test_bgp_proto_group_name))
                if router_params2['mx_asn'] > self.AS_2BYTE_MAX:
                    peer_asn = self.AS_TRANS
            cmds1.append("set groups %s protocols bgp group %s peer-as %s" %
                         (test_group_name, test_bgp_proto_group_name, peer_asn))

            cmds1.append(
                "set groups %s routing-instances ri_4byte_ext instance-type vrf" % test_group_name)
            cmds1.append("set groups %s routing-instances ri_4byte_ext interface %s.10" %
                         (test_group_name, router_params['vrf_interface']))
            cmds1.append("set groups %s routing-instances ri_4byte_ext route-distinguisher %s:10" %
                         (test_group_name, router_params['vrf_interface_ip']))
            cmds1.append("set groups %s routing-instances ri_4byte_ext vrf-target %s" %
                         (test_group_name, vrf_target))
            cmds1.append(
                "set groups %s routing-instances ri_4byte_ext vrf-table-label" % (test_group_name))

            cmds1.append("set groups %s routing-options dynamic-tunnels 4byte source-address %s" %
                         (test_group_name, router_params['loopback_ip']))
            cmds1.append(
                "set groups %s routing-options dynamic-tunnels 4byte gre" % test_group_name)
            cmds1.append("set groups %s routing-options dynamic-tunnels 4byte destination-networks %s/32" %
                         (test_group_name, router_params2['loopback_ip']))

            cmds1.append("set groups %s" % test_group_name)
            cmds1.append("set apply-groups %s" % test_group_name)

            cleanup_cmds = []
            self.provision_mx(
                router_params['mgmt_ip'], cmds1, cleanup_cmds, ignore_errors=True)

            if router_params['remote_mx']:
                cmds2 = []
                cleanup_cmds = []

                cmds2.append(
                    "set groups %s policy-options policy-statement export_static from protocol static" % (test_group_name))
                static_routes = router_params['static_routes']
                addnl_static_routes = router_params['addnl_static_routes']
                aggr_route = router_params['aggr_route']
                for route in addnl_static_routes:
                    cmds2.append(
                        "set groups %s policy-options policy-statement export_static from route-filter %s exact" % (test_group_name, route))
                for route in static_routes:
                    cmds2.append(
                        "set groups %s policy-options policy-statement export_static from route-filter %s exact" % (test_group_name, route))
                cmds2.append(
                    "set groups %s policy-options policy-statement export_static then community add 2byte" % (test_group_name))
                cmds2.append(
                    "set groups %s policy-options policy-statement export_static then accept" % (test_group_name))
                cmds2.append(
                    "set groups %s policy-options policy-statement export_aggr from protocol aggregate" % (test_group_name))
                cmds2.append(
                    "set groups %s policy-options policy-statement export_aggr then community add 2byte" % (test_group_name))
                cmds2.append(
                    "set groups %s policy-options policy-statement export_aggr then accept" % (test_group_name))
                cmds2.append("set groups %s policy-options community 2byte members %s" %
                             (test_group_name, vrf_target))

                cmds2.append(
                    "set groups %s routing-instances ri_4byte_ext vrf-export export_static" % (test_group_name))
                cmds2.append(
                    "set groups %s routing-instances ri_4byte_ext vrf-export export_aggr" % (test_group_name))
                for route in addnl_static_routes:
                    cmds2.append(
                        "set groups %s routing-instances ri_4byte_ext routing-options static route %s discard" % (test_group_name, route))
                for route in static_routes:
                    cmds2.append(
                        "set groups %s routing-instances ri_4byte_ext routing-options static route %s discard" % (test_group_name, route))
                cmds2.append("set groups %s routing-instances ri_4byte_ext routing-options aggregate route %s policy export_static" %
                             (test_group_name, aggr_route))
                self.provision_mx(
                    router_params['mgmt_ip'], cmds2, cleanup_cmds, ignore_errors=True)

    def mx_create_vrf(self, control_node_config, mx_config, vn_fixture=None):
        self.logger.info("Create VRF configuration in MX")

        test_group_name = mx_config['test_group_name']
        ri_name = mx_config['ri_name']
        ri_interface = mx_config["vrf_interface"]
        rd = mx_config["rd"]
        if vn_fixture:
            vrf_target = self.get_vrf_target(control_node_config, vn_fixture)
        else:
            vrf_target = mx_config["vrf_target"]
        cmds = []
        cmds.append("set groups %s routing-instances %s instance-type vrf" %
                    (test_group_name, ri_name))
        cmds.append("set groups %s routing-instances %s interface %s" %
                    (test_group_name, ri_name, ri_interface))
        cmds.append("set groups %s routing-instances %s route-distinguisher %s" %
                    (test_group_name, ri_name, rd))
        cmds.append("set groups %s routing-instances %s vrf-target %s" %
                    (test_group_name, ri_name, vrf_target))
        cmds.append("set groups %s routing-instances %s vrf-table-label" %
                    (test_group_name, ri_name))
        cleanup_cmds = []
        self.provision_mx(mx_config['control_ip'], cmds, cleanup_cmds)

    def deactivate_mx_cluster_configuration(self, mx_config):
        self.logger.info("deactivate MX cluster configuration")
        bgp_protocol_group = mx_config['bgp_protocol_group']
        cluster_group = mx_config['cluster_group']
        cmds = []
        if bgp_protocol_group:
            cmds.append("deactivate protocols bgp group %s" %
                        bgp_protocol_group)
        if cluster_group:
            cmds.append("delete apply-groups %s" % cluster_group)
        cleanup_cmds = []
        self.provision_mx(mx_config['control_ip'],
                          cmds, cleanup_cmds, ignore_errors=True)

    def activate_mx_cluster_configuration(self, mx_config):
        self.logger.info("activate mx cluster configuration")
        self.cleanup_mx_basic_bgp_test_configuration(mx_config)
        bgp_protocol_group = mx_config['bgp_protocol_group']
        cluster_group = mx_config['cluster_group']
        cmds = []
        if bgp_protocol_group:
            cmds.append("activate protocols bgp group %s" % bgp_protocol_group)
        if cluster_group:
            cmds.append("set apply-groups %s" % cluster_group)

        cleanup_cmds = []
        self.provision_mx(mx_config['control_ip'],
                          cmds, cleanup_cmds, ignore_errors=True)

    def cleanup_mx_basic_bgp_test_configuration(self, mx_config):
        test_group_name = mx_config['test_group_name']
        cmds = []
        cleanup_cmds = []
        cmds.append('delete groups %s' % test_group_name)
        cmds.append("delete apply-groups %s" % test_group_name)
        self.provision_mx(mx_config['control_ip'],
                          cmds, cleanup_cmds, ignore_errors=True)

    def mx_basic_bgp_test_configuration(self, mx_config, peer_config, skip_cleanup=False):

        cluster_group_name = mx_config['group']
        test_group_name = mx_config['test_group_name']
        test_bgp_group_name = mx_config['test_bgp_proto_group_name']
        mx_asn = mx_config['asn']
        peer_ips = peer_config['peer_ips']
        peer_as = peer_config['peer_asn']
        local_address = mx_config['tunnel_ip']
        address_family = ["inet unicast", "inet-vpn unicast",
                          "inet6-vpn unicast", "route-target"]
        mx_4b_capability = mx_config['mx_4b_capability']

        if not mx_4b_capability and peer_as > self.AS_2BYTE_MAX:
            peer_as = self.AS_TRANS

        cmds = []
        cleanup_cmds = []
        if cluster_group_name:
            cmds.append("delete apply-groups %s" % cluster_group_name)
            self.provision_mx(mx_config['control_ip'],
                              cmds, cleanup_cmds, ignore_errors=True)
        cmds = []
        cmds.append("delete groups %s" % test_group_name)
        cmds.append("delete apply-groups %s" % test_group_name)
        self.provision_mx(mx_config['control_ip'],
                          cmds, cleanup_cmds, ignore_errors=True)

        cmds = []
        cmds.append("set routing-options autonomous-system %d" % mx_asn)
        cmds.append("set groups %s routing-options autonomous-system %d" %
                    (test_group_name, mx_asn))
        if mx_asn == peer_as:
            cmds.append("set groups %s protocols bgp group %s type internal" % (
                test_group_name, test_bgp_group_name))
        else:
            cmds.append("set groups %s protocols bgp group %s type external" % (
                test_group_name, test_bgp_group_name))
        cmds.append("set groups %s protocols bgp group %s traceoptions file bgp_log" % (
            test_group_name, test_bgp_group_name))
        cmds.append("set groups %s protocols bgp group %s traceoptions file size 4294967295" % (
            test_group_name, test_bgp_group_name))
        cmds.append("set groups %s protocols bgp group %s traceoptions file world-readable" %
                    (test_group_name, test_bgp_group_name))
        cmds.append("set groups %s protocols bgp group %s local-address %s" %
                    (test_group_name, test_bgp_group_name, local_address))
        cmds.append("set groups %s routing-options router-id %s" %
                    (test_group_name, local_address))
        for family in address_family:
            cmds.append("set groups %s protocols bgp group %s family %s" %
                        (test_group_name, test_bgp_group_name, family))
        cmds.append("set groups %s protocols bgp group %s local-as %d" %
                    (test_group_name, test_bgp_group_name, mx_asn))
        cmds.append("set groups %s protocols bgp group %s peer-as %d" %
                    (test_group_name, test_bgp_group_name, peer_as))
        for peer_ip in peer_ips:
            cmds.append("set groups %s protocols bgp group %s neighbor %s" % (
                test_group_name, test_bgp_group_name, peer_ip))

        if not mx_4b_capability:
            cmds.append("set groups %s protocols bgp group %s disable-4byte-as" %
                        (test_group_name, test_bgp_group_name))

        cmds.append("set apply-groups %s" % test_group_name)

        cleanup_cmds = []

        self.provision_mx(mx_config['control_ip'], cmds, cleanup_cmds)

    def cleanup_mx(self, mx_ip, cmds):

        mx_handle = NetconfConnection(host=mx_ip)
        mx_handle.connect()
        cli_output = mx_handle.config(stmts=cmds, timeout=120)
        mx_handle.disconnect()
        assert (not('failed' in cli_output)), "Not able to push config to mx"

    def provision_mx(self, device_ip, cli_cmds, cleanup_cmds, ignore_errors=False):

        mx_handle = NetconfConnection(host=device_ip)
        mx_handle.connect()
        cli_output = mx_handle.config(
            stmts=cli_cmds, ignore_errors=ignore_errors, timeout=120)
        mx_handle.disconnect()
        assert cli_output[0], "Not able to push config to mx"

        self.addCleanup(self.cleanup_mx, device_ip, cleanup_cmds)
