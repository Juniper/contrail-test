#
# OpServer Utils
#
# Utility functions for Operational State Server for VNC
#
# Created by Sandip Dey on 24/09/2013
#
# Copyright (c) 2013, Contrail Systems, Inc. All rights reserved.
#

import datetime
import time
import requests
import pkg_resources
import xmltodict
import json
import gevent
import logging as LOG

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.INFO)

try:
    from pysandesh.gen_py.sandesh.ttypes import SandeshType
except:
    class SandeshType(object):
        SYSTEM = 1
        TRACE = 4


def enum(**enums):
    return type('Enum', (), enums)
# end enum


class DiscoveryServerUtils(object):

    TIME_FORMAT_STR = '%Y %b %d %H:%M:%S.%f'
    DEFAULT_TIME_DELTA = 10 * 60 * 1000000  # 10 minutes in microseconds
    USECS_IN_SEC = 1000 * 1000
    OBJECT_ID = 'ObjectId'

#    POST_HEADERS = {'Content-type': 'application/json; charset="UTF-8"', 'Expect':'202-accepted'}
    POST_HEADERS = {'Content-type': 'application/json'}

    @staticmethod
    def post_url_http(url, params):
        try:
            if int(pkg_resources.get_distribution("requests").version[0]) == 1:
                response = requests.post(url, stream=True,
                                         data=params,
                                         headers=DiscoveryServerUtils.POST_HEADERS)
            else:
                response = requests.post(url,
                                         data=params,
                                         headers=DiscoveryServerUtils.POST_HEADERS)
        except requests.exceptions.ConnectionError, e:
            print "Connection to %s failed" % url
            return None
        print 'response: %s' % (response)
        if response.status_code == 200:
            return response.text
        else:
            print "HTTP error code: %d" % response.status_code
        return None
    # end post_url_http

    @staticmethod
    def put_url_http(url, params):
        try:
            if int(pkg_resources.get_distribution("requests").version[0]) == 1:
                response = requests.put(url, stream=True,
                                         data=params,
                                         headers=DiscoveryServerUtils.POST_HEADERS)
            else:
                response = requests.put(url,
                                         data=params,
                                         headers=DiscoveryServerUtils.POST_HEADERS)
        except requests.exceptions.ConnectionError, e:
            LOG.error("Connection to %s failed", url)
            return None
        LOG.info("response: %s" % response)
        if response.status_code == 200:
            return response.text
        else:
            LOG.error("HTTP error code: %d" % response.status_code)
        return None
    # end put_url_http

    @staticmethod
    def get_url_http(url):
        data = None
        try:
            if int(pkg_resources.get_distribution("requests").version[0]) == 1:
                data = requests.get(url, stream=True)
            else:
                data = requests.get(url)
        except requests.exceptions.ConnectionError, e:
            print "Connection to %s failed" % url
        if data.status_code == 200:
            return data.text
        else:
            print "HTTP error code: %d" % response.status_code
        return None

    # end get_url_http

    @staticmethod
    def discovery_url(ip, port):
        return "http://" + ip + ":" + port
    # end discovery_url

    @staticmethod
    def discovery_publish_service_url(discovery_ip, discovery_port):
        return "http://" + discovery_ip + ":" + discovery_port + "/publish"
    # end discovery_query_url

    @staticmethod
    def discovery_subscribe_service_url(discovery_ip, discovery_port):
        return "http://" + discovery_ip + ":" + discovery_port + "/subscribe"
    # end discovery_query_url

    @staticmethod
    def discovery_cleanup_service_url(discovery_ip, discovery_port):
        return "http://" + discovery_ip + ":" + discovery_port + "/cleanup"
    # end discovery_query_url

    @staticmethod
    def messages_xml_data_to_dict(messages_dict, msg_type):
        if msg_type in messages_dict:
            # convert xml value to dict
            try:
                messages_dict[msg_type] = xmltodict.parse(
                    messages_dict[msg_type])
            except:
                pass
    # end messages_xml_data_to_dict

    @staticmethod
    def messages_data_dict_to_str(messages_dict, message_type, sandesh_type):
        data_dict = messages_dict[message_type]
        return DiscoveryServerUtils._data_dict_to_str(data_dict, sandesh_type)
    # end messages_data_dict_to_str

# end class DiscoveryServerUtils
