from common.neutron.attributes import *
import testtools
import json

from tcutils.util import *
from tcutils.wrappers import preposttest_wrapper
from common.neutron.neutron_util import combos
from common.neutron.base import BaseNeutronTest
import test

from common.openstack_libs import neutron_client as client
from common.openstack_libs import neutron_http_client as HTTPClient
from common.openstack_libs import neutron_exception as NeutronClientException
from common.openstack_libs import ks_client as ksclient
from common.openstack_libs import ks_exceptions

class TestCRUD(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestCRUD, cls).setUpClass()

    def setUp(self):
        super(TestCRUD, self).setUp()
        self.neutron_test_h = self.admin_connections.quantum_h
        self.neutron_h = self.admin_connections.quantum_h.obj
        self.proj_neutron_test_h = self.quantum_h
        self.proj_neutron_h = self.quantum_h.obj

        self.create_security_group(get_random_name('admin-sg1'),
                                   self.neutron_test_h)
        self.create_security_group(get_random_name('admin-sg2'),
                                   self.neutron_test_h)
        self.create_security_group(get_random_name('proj-sg1'),
                                   self.proj_neutron_test_h)
        self.create_security_group(get_random_name('proj-sg2'),
                                   self.proj_neutron_test_h)
        self.ks_project_id = self.project.uuid
        self.log = self.logger
        self.newline = '=' * 80 + '\n'
    # end setUp

    def cleanUp(self):
        super(TestCRUD, self).cleanUp()

    @classmethod
    def tearDownClass(cls):
        super(TestCRUD, cls).tearDownClass()

    @preposttest_wrapper
    def test_network_subnet_port_crud(self):
        count = 0
        # project1 tenant-id for now
        #proj1_id = self.project1_obj.id
        proj1_id = self.ks_project_id
        for attribute_list in combos(get_other_network_create_attributes()):
            body = {}
            count += 1
            print count
            for attribute in attribute_list:
                body[attribute] = get_random_value(network, attribute)
            for attribute in get_network_create_required_attributes():
                body[attribute] = get_random_value(attribute)
            if 'tenant_id' in attribute_list:
                body['tenant_id'] = proj1_id
            # TODO
            # Workaround so that name is present always
            if 'name' not in body.keys():
                continue
            body = {'network': body}
            self.log.info("Network Create Request %s" % (body))
            response = None
            try:
                response = self.neutron_h.create_network(body)
                self.log.info("Network Create Response : %s" % (response))
                self.addCleanup(self._delete_network, response['network']['id'])
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with neutron "\
                              "create network : %s" % (e, body)
            assert response and response['network'],\
                "Network Create request FAILED!!,"\
                " Body : %s, Response : %s" % (body, response)
            self.log.info("Network create request PASSED , Body : "
                          "%s" % (body))
            # Do read tests
            self.read_network_tests(response['network'])
            # Do update tests
            self.update_network_tests(response['network'])
            # Do Subnet tests
            self._test_subnets(response['network'])
            self._delete_network(response['network']['id'])
            self.log.info(self.newline)
    # end test_network_subnet_port_crud

    def read_network_tests(self, network):
        result = True
        network_obj = network
        net_id = network_obj['id']
        try:
            response = self.neutron_h.show_network(net_id)
        except NeutronClientException, e:
            assert False, "NeutronClientException %s with show_network : "\
                "%s" % (e)

        for attribute in get_network_read_attributes():
            assert response['network'][attribute] == network_obj[attribute],\
                'Attribute %s did not seem to be created!, '\
                'Expected: %s, Got: %s ' % (
                    attribute, network_obj[attribute],
                    response['network'][attribute])
            self.log.info('Attribute %s is created' % (attribute))
        # end for attribute

        for attribute_list in combos(get_network_read_attributes()):
            fields = {'fields': []}
            for attribute in attribute_list:
                fields['fields'].append(attribute)
            item_count = len(fields['fields'])
            try:
                response = self.neutron_h.show_network(net_id, **fields)
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with show_network :"\
                              "%s" % (e)
            assert len(response['network']) == item_count,\
                "Mismatch in number of fields returned!"\
                "Expected : %s, Got : %s" % (fields, response['network'])
        # end attribute_list
    # end read_network_tests

    def update_network_tests(self, network_obj):
        proj1_id = self.ks_project_id
        net_id = network_obj['id']
        for attribute_list in combos(get_network_update_attributes()):
            body = {}
            for attribute in attribute_list:
                body[attribute] = get_random_value(network, attribute)
            body = {'network': body}
            self.log.info("Network Update request %s" % (body))
            response = None
            try:
                response = self.neutron_h.update_network(net_id, body)
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with neutron update"\
                    " network : %s" % (e, body)
            assert response and response['network'],\
                "Network Update request FAILED!!, Body : %s"\
                " Response: %s" % (body, response)
            self.log.info("Network Update request PASS,Body : %s" % (body))
            self.log.info("Response : %s" % (response))
            for attribute in attribute_list:
                assert compare(body['network'][attribute],
                               response['network'][attribute]),\
                    "Network update on attribute failed!"\
                    "Expected: %s, Got : %s" % (
                        body['network'][attribute],
                        response['network'][attribute])
            # end for attribute
            self.log.info("Update of Network %s, body %s passed" % (
                          net_id, body))
            self.log.info('-' * 80)
        # end for attribute_list
    # end update_network_test

    @run_once
    def _test_subnets(self, network_obj):
        count = 0
        # project1 tenant-id for now
        proj1_id = self.ks_project_id
        net_id = network_obj['id']
        for attribute_list in combos(get_other_subnet_create_attributes()):
            body = {}
            count += 1
            print count
            for attribute in get_subnet_create_required_attributes():
                body[attribute] = get_random_value(subnet, attribute)
            for attribute in attribute_list:
                if attribute in ['gateway_ip', 'allocation_pools',
                                 'host_routes']:
                    body[attribute] = get_random_value(subnet,
                                                       attribute, body['cidr'])
                else:
                    body[attribute] = get_random_value(subnet, attribute)
            if 'tenant_id' in attribute_list:
                body['tenant_id'] = network_obj['tenant_id']
            body['network_id'] = net_id
            body = {'subnet': body}
            self.log.info("Subnet Create request %s" % (body))
            response = None
            try:
                response = self.neutron_h.create_subnet(body)
                self.log.info("Subnet create Response : %s" % (response))
                self.addCleanup(self._delete_subnet, response['subnet']['id'])
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with create \
                                subnet : %s" % (e, body)
            assert response and response['subnet'],\
                "Subnet Create request FAILED!!, Body : %s, Response : %s" % (
                    body, response)
            self.log.info("Subnet create request PASSED , Body : %s" % (
                body))
            subnet_id = response['subnet']['id']
            # Do read tests
            self.read_subnet_tests(response['subnet'])
            # Do port tests
            self._test_ports(network_obj, response['subnet'])
            # Do update tests
            self.update_subnet_tests(response['subnet'])
            self._delete_subnet(response['subnet']['id'])
            self.log.info(self.newline)
    # end

    @run_once
    def read_subnet_tests(self, subnet):
        result = True
        subnet_obj = subnet
        subnet_id = subnet_obj['id']
        try:
            response = self.neutron_h.show_subnet(subnet_id)
        except NeutronClientException, e:
            assert False,\
                "NeutronClientException %s with show_subnet: %s" % (e)

        for attribute in get_subnet_read_attributes():
            assert response['subnet'][attribute] == subnet_obj[attribute],\
                'Attribute %s did not seem to be created!, '\
                'Expected: %s, Got: %s ' % (
                    attribute, subnet_obj[attribute],
                    response['subnet'][attribute])
            self.log.info('Attribute %s is created' % (attribute))
        # end for attribute

        for attribute_list in combos(get_subnet_read_attributes()):
            fields = {'fields': []}
            for attribute in attribute_list:
                fields['fields'].append(attribute)
            item_count = len(fields['fields'])
            try:
                response = self.neutron_h.show_subnet(subnet_id, **fields)
            except NeutronClientException, e:
                assert False,\
                    "NeutronClientException %s with show_subnet: %s" % (e)
            assert len(response['subnet']) == item_count,\
                "Mismatch in number of fields returned!"\
                "Expected : %s, Got : %s" % (fields, response['subnet'])
        # end attribute_list
        self.log.info("Subnet show with fields %s passed" % (
                      fields['fields']))
    # end read_subnet_tests

    @run_once
    def update_subnet_tests(self, subnet_obj):
        result = True
        subnet_id = subnet_obj['id']
        for attribute_list in combos(get_subnet_update_attributes()):
            body = {}
            for attribute in attribute_list:
                if attribute in ['gateway_ip', 'allocation_pools',
                                 'host_routes']:
                    body[attribute] = get_random_value(subnet,
                                                       attribute, subnet_obj['cidr'])
                else:
                    body[attribute] = get_random_value(subnet, attribute)

            body = {'subnet': body}
            self.log.info("Subnet Update request %s" % (body))
            response = None
            try:
                response = self.neutron_h.update_subnet(subnet_id, body)
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with Subnet update "\
                    "network : %s" % (e, body)
            assert response and response['subnet'],\
                "Subnet Update request FAILED!!, Body : %s, Response: %s" % (
                    body, response)
            self.log.info("Subnet Update request PASSED , Body : %s" %
                          (body))
            self.log.info("Subnet Update Response : %s" % (response))
            updated = True
            for attribute in attribute_list:
                assert compare(body['subnet'][attribute],
                               response['subnet'][attribute]),\
                    "Subnet update on attribute failed!"\
                    "Expected : %s, Got : %s" % (
                        body['subnet'][attribute],
                        response['subnet'][attribute])
            self.log.info("Updation of Subnet %s with body %s passed" % (
                subnet_id, body))
            self.log.info('-' * 80)
        # end for attribute_list
    # end update_subnet_tests

    def get_sgs(self, project_id):
        return [x['id'] for x in self.neutron_h.list_security_groups(
            tenant_id=project_id)['security_groups']]

    def get_random_sg_list(self, project_id):
        sg_list = self.get_sgs(project_id)
        random.shuffle(sg_list)
        length = random.randint(0, len(sg_list) - 1)
        return sg_list[0:length]

    @run_once
    def _test_ports(self, network_obj, subnet_obj):
        net_id = network_obj['id']
        subnet_id = subnet_obj['id']

        count = 1
        for attribute_list in combos(get_other_port_create_attributes()):
            body = {}
            count += 1
            print count
            for attribute in get_port_create_required_attributes():
                body[attribute] = get_random_value(port, attribute)
            for attribute in attribute_list:
                if attribute in ['fixed_ips']:
                    body[attribute] = get_random_value(port,
                                                       attribute, subnet_id, subnet_obj['cidr'])
                elif attribute in 'tenant_id':
                    body['tenant_id'] = network_obj['tenant_id']
                elif attribute in 'security_groups':
                    body['security_groups'] = self.get_random_sg_list(
                        network_obj['tenant_id'])
                else:
                    body[attribute] = get_random_value(port, attribute)
            body['network_id'] = net_id
            body = {'port': body}
            self.log.info("Port Create request %s" % (body))
            response = None
            try:
                response = self.neutron_h.create_port(body)
                self.log.info("Port create Response : %s" % (response))
                self.addCleanup(self._delete_port, response['port']['id'])
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with create port:"\
                    "%s" % (e, body)
            assert response and response['port'],\
                "Port Create request FAILED!!, Body : %s, Response : %s"\
                % (body, response)
            self.log.info("Port create request PASSED ,Body : %s" % (body))
            port_id = response['port']['id']
            port_obj = response['port']
            # Do read tests
            self.read_port_tests(port_obj)
            # Do update tests
            self.update_port_tests(port_obj, network_obj, subnet_obj)
            self._delete_port(response['port']['id'])
            self.log.info(self.newline)
    # end

    def _delete_port(self, port_id):
        if self._remove_from_cleanup(self._delete_port, (port_id)):
            self.log.info('Deleting port %s' % (port_id))
            try:
                result = self.neutron_h.delete_port(port_id)
                if result != "":
                    self.log.error('Result of delete port %s: %s' % (port_id,
                                                                     result))
                    return False
            except NeutronClientException, e:
                self.log.exception(e)
                return False
        return True

    def _delete_network(self, network_id):
        if self._remove_from_cleanup(self._delete_network, (network_id)):
            self.log.info('Deleting network %s' % (network_id))
            try:
                result = self.neutron_h.delete_network(network_id)
                if result != "":
                    self.log.error('Result of delete network %s: %s' % (
                                    network_id, result))
                    return False
            except NeutronClientException, e:
                self.log.exception(e)
                return False
        return True

    def _delete_subnet(self, subnet_id):
        if self._remove_from_cleanup(self._delete_subnet, (subnet_id)):
            self.log.info('Deleting subnet %s' % (subnet_id))
            try:
                result = self.neutron_h.delete_subnet(subnet_id)
                if result != "":
                    self.log.error('Result of delete subnet %s: %s' % (
                                    subnet_id, result))
                    return False
            except NeutronClientException, e:
                self.log.exception(e)
                return False
        return False

    def _delete_router(self, router_id):
        if self._remove_from_cleanup(self._delete_router, (router_id)):
            self.log.info('Deleting router %s' % (router_id))
            try:
                result = self.neutron_h.delete_router(router_id)
                if result != "":
                    self.log.error('Result of delete router %s: %s' % (
                                    router_id, result))
                    return False
            except NeutronClientException, e:
                self.log.exception(e)
                return False
        return True

    @run_once
    def read_port_tests(self, port_obj):
        result = True
        port_id = port_obj['id']
        try:
            response = self.neutron_h.show_port(port_id)
        except NeutronClientException, e:
            assert False, "NeutronClientException %s with show_port: %s" % (e)

        for attribute in get_port_read_attributes():
            assert response['port'][attribute] == port_obj[attribute],\
                'Attribute %s did not seem to be present!, '\
                'Expected: %s, Got: %s ' % (
                    attribute, port_obj[attribute], response['port'][attribute])
            self.log.info('Attribute %s is present' % (attribute))
        # end for attribute

        for attribute_list in combos(get_port_read_attributes()):
            fields = {'fields': []}
            for attribute in attribute_list:
                fields['fields'].append(attribute)
            item_count = len(fields['fields'])
            try:
                response = self.neutron_h.show_port(port_id, **fields)
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with show_port with"\
                              " fields : %s" % (e)
            assert len(response['port']) == item_count,\
                "Mismatch in number of fields returned!"\
                "Expected : %s, Got: %s" % (fields, response['port'])
            self.log.info("Port show with fields %s passed" % (fields))
        # end attribute_list
    # end read_port_tests

    @run_once
    def update_port_tests(self, port_obj, network_obj, subnet_obj):
        net_id = network_obj['id']
        subnet_id = subnet_obj['id']
        port_id = port_obj['id']
        for attribute_list in combos(get_port_update_attributes()):
            body = {}
            for attribute in attribute_list:
                if attribute in ['fixed_ips']:
                    body[attribute] = get_random_value(port,
                                                       attribute, subnet_id, subnet_obj['cidr'])
                elif attribute in 'tenant_id':
                    body['tenant_id'] = network_obj['tenant_id']
                elif attribute in 'security_groups':
                    body['security_groups'] = self.get_random_sg_list(
                        network_obj['tenant_id'])
                else:
                    body[attribute] = get_random_value(port, attribute)
            body = {'port': body}
            self.log.info("Port Update request %s" % (body))
            response = None
            try:
                response = self.neutron_h.update_port(port_id, body)
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with update \
                    port : %s" % (e, body)
            assert response and response['port'],\
                "Port Update request FAILED!, Body: %s, Response : %s" % (
                    body, response)
            self.log.info("Port Update request PASSED , Body : %s" % (body))
            self.log.info("Port Update Response : %s" % (response))
            updated = True
            for attribute in attribute_list:
                assert compare(body['port'][attribute],
                               response['port'][attribute]),\
                    "Port update on attribute failed!"\
                    "Expected : %s, Got : %s" % (
                        body['port'][attribute], response['port'][attribute])
            self.log.info("On update, Verification of attributes of Port %s "
                          "with body %s passed" % (port_id, body))
            self.log.info('-' * 80)
        # end for attribute_list
    # end update_port_tests

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_router_crud(self):
        count = 0
        proj1_id = self.ks_project_id
        for attribute_list in combos(get_other_router_create_attributes()):
            body = {}
            count += 1
            print count
            for attribute in attribute_list:
                body[attribute] = get_random_value(router, attribute)
            for attribute in get_router_create_required_attributes():
                body[attribute] = get_random_value(attribute)
            if 'tenant_id' in attribute_list:
                body['tenant_id'] = proj1_id
            # TODO
            # Workaround so that name is present always
            if 'name' not in body.keys():
                continue
            body = {'router': body}
            self.log.info("Router create Request %s" % (body))
            response = None
            try:
                response = self.neutron_h.create_router(body)
                self.log.info("Router create Response : %s" % (response))
                self.addCleanup(self._delete_router, response['router']['id'])
            except NeutronClientException, e:
                assert False, "NeutronClientException %s with neutron create "\
                              "router : %s" % (e, body)
            assert response and response['router'],\
                "Router Create request FAILED!!, Body : %s, Response : %s" % (
                    body, response)
            self.log.info("Router create PASSED ,Body : %s" % (body))
            # Do read tests
            self.read_router_tests(response['router'])
            # Do update tests
            self.update_router_tests(response['router'])
            self._delete_router(response['router']['id'])
            self.log.info(self.newline)
    # end

    def read_router_tests(self, router):
        result = True
        router_obj = router
        router_id = router_obj['id']
        try:
            response = self.neutron_h.show_router(router_id)
        except NeutronClientException, e:
            assert False, "NeutronClientException %s with show_router : %s" % (
                e)

        for attribute in get_router_read_attributes():
            assert response['router'][attribute] == router_obj[attribute],\
                'Attribute %s did not seem to be created!, '\
                'Expected: %s, Got: %s ' % (
                    attribute, router_obj[attribute], response['router'][attribute])
            self.log.info('Attribute %s is created' % (attribute))
        # end for attribute

        for attribute_list in combos(get_router_read_attributes()):
            fields = {'fields': []}
            for attribute in attribute_list:
                fields['fields'].append(attribute)
            item_count = len(fields['fields'])
            try:
                response = self.neutron_h.show_router(router_id, **fields)
            except NeutronClientException, e:
                assert False,\
                    "NeutronClientException rs with show_router:  %s" % (e)
            assert len(response['router']) == item_count,\
                "Mismatch in number of fields returned!"\
                "Expected : %s, Got : %s" % (fields, response['router'])
        # end attribute_list
        self.log.info("Router show with fields %s passed" % (
                      fields['fields']))
    # end read_router_tests

    def update_router_tests(self, router_obj):
        proj1_id = self.ks_project_id
        router_id = router_obj['id']
        for attribute_list in combos(get_router_update_attributes()):
            body = {}
            for attribute in attribute_list:
                body[attribute] = get_random_value(router, attribute)
            body = {'router': body}
            self.log.info("Router Update request %s" % (body))
            response = None
            try:
                response = self.neutron_h.update_router(router_id, body)
            except NeutronClientException, e:
                assert False,\
                    "NeutronClientException %s with router update : %s" % (
                        e, body)
            assert response and response['router'],\
                "Router Update request FAILED!!,  "\
                "Body : %s, Response : %s" % (body, response)
            self.log.info("Router Update request PASSED,Body : %s" % (body))
            self.log.info("Response : %s" % (response))
            updated = True
            for attribute in attribute_list:
                assert compare(body['router'][attribute],
                               response['router'][attribute]),\
                    "Router update on attribute failed!"\
                    "Expected : %s, Got : %s" % (
                        body['router'][attribute], response['router'][attribute])
            self.log.info("Updation of Router %s with body %s passed" % (
                          router_id, body))
            self.log.info('-' * 80)
        # end for attribute_list
    # end update_router_test

# end class TestCRUD
