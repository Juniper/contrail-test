# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#import netaddr

#from tempest.api.network import base
#from tempest.common.utils.data_utils import rand_name
#from tempest import exceptions
#from tempest.test import attr
import unittest
import fixtures
import testtools


#class NetworksTestJSON(base.BaseNetworkTest):
class NetworksTestJSON(testtools.TestCase,fixtures.TestWithFixtures):
#    _interface = 'json'


    @classmethod
    def setUpClass(cls):
        super(NetworksTestJSON,cls).setUpClass()
#        cls.network = cls.create_network()
#        cls.name = cls.network['name']
#        cls.subnet = cls.create_subnet(cls.network)
#        cls.cidr = cls.subnet['cidr']
#        cls.port = cls.create_port(cls.network)

#    @attr(type='smoke')
    def test_create_update_delete_network_subnet(self):
        # Creates a network
	print 'aaaaaaaaaa'
	pass
#    @attr(type='smoke')
    def test_show_network(self):
        # Verifies the details of a network
	print 'aaaaaaaaaa'
	pass

#    @attr(type='smoke')
    def test_list_networks(self):
	print 'aaaaaaaaaa'
	pass

#    @attr(type='smoke')
    def test_show_subnet(self):
	print 'aaaaaaaaaa'
	pass
        # Verifies the details of a subnet

#    @attr(type='smoke')
    def test_list_subnets(self):
        # Verify the subnet exists in the list of all subnets
	print 'aaaaaaaaaa'
	pass

#    @attr(type='smoke')
    def test_create_update_delete_port(self):
        # Verify that successful port creation, update & deletion
	print 'aaaaaaaaaa'
	pass

#    @attr(type='smoke')
    def test_show_port(self):
        # Verify the details of port
	print 'aaaaaaaaaa'
	pass

#    @attr(type='smoke')
    def test_list_ports(self):
        # Verify the port exists in the list of all ports
	print 'aaaaaaaaaa'
	pass

#    @attr(type=['negative', 'smoke'])
    def test_show_non_existent_network(self):
	print 'aaaaaaaaaa'
	pass


#    @attr(type=['negative', 'smoke'])
    def test_show_non_existent_subnet(self):
	print 'aaaaaaaaaa'
	pass

#    @attr(type=['negative', 'smoke'])
    def test_show_non_existent_port(self):
	print 'aaaaaaaaaa'
	pass


class NetworksTestXML(NetworksTestJSON):
#    _interface = 'xml'
    pass	


