#
# Traces Utils
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
from lxml import etree
import socket
import sys
import argparse
import ConfigParser
import os

try:
    from pysandesh.gen_py.sandesh.ttypes import SandeshType
except:
    class SandeshType(object):
        SYSTEM = 1
        TRACE = 4


def enum(**enums):
    return type('Enum', (), enums)
# end enum


class TraceUtils(object):

    TIME_FORMAT_STR = '%Y %b %d %H:%M:%S.%f'
    DEFAULT_TIME_DELTA = 10 * 60 * 1000000  # 10 minutes in microseconds
    USECS_IN_SEC = 1000 * 1000
    OBJECT_ID = 'ObjectId'

#    POST_HEADERS = {'Content-type': 'application/json; charset="UTF-8"', 'Expect':'202-accepted'}
    POST_HEADERS = {'Content-type': 'application/json'}

    def __init__(self, args_str=None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        TraceUtils.get_trace_buffer(
            self._args.server_ip, self._args.server_port, self._args.buffer_name,
            self._args.filename, self._args.opserver_ip, self._args.node_name, self._args.module)

    def _parse_args(self, args_str):
        '''
        Eg. python trace_util.py
                                        --server_ip 127.0.0.1
                                        --server_port 8083
                                        --buffer_name  None/'DiscoveryClient'
                                        --filename 
                                        --opserver_ip
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        defaults = {
            'server_ip': '127.0.0.1',
            'server_port': '',
            'buffer_name': '',
            'filename': '',
            'opserver_ip': '',
            'node_name': '',
            'module': '',
        }

        ksopts = {
            'admin_user': 'user1',
            'admin_password': 'password1',
            'admin_tenant_name': 'admin'
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            defaults.update(dict(config.items("DEFAULTS")))
            if 'KEYSTONE' in config.sections():
                ksopts.update(dict(config.items("KEYSTONE")))

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
        defaults.update(ksopts)
        parser.set_defaults(**defaults)

        parser.add_argument(
            "--server_ip", help="IP address of server for which traces needs to collected")
        parser.add_argument("--server_port",
                            help="Port of server depending on the role")
        parser.add_argument(
            "--buffer_name", help="buffer name, if not given all the buffers to files")
        parser.add_argument(
            "--filename", help="file name to save buffers;location /var/log/contrail/traces")
        parser.add_argument(
            "--opserver_ip", help="opserver ip in case want to save the traces to database")
        parser.add_argument(
            "--node_name", help="Node name in case want to save the traces to database")
        parser.add_argument(
            "--module", help="module in case want to save the traces to database")
        parser.add_argument(
            "--admin_user", help="Name of keystone admin user")
        parser.add_argument(
            "--admin_password", help="Password of keystone admin user")

        self._args = parser.parse_args(remaining_argv)

    # end _parse_args

    @staticmethod
    def get_url_http(url):
        data = None
        try:
            if int(pkg_resources.get_distribution("requests").version[0]) == 1:
                data = requests.get(url, stream=True)
            else:
                data = requests.get(url, prefetch=False)
        except requests.exceptions.ConnectionError, e:
            print "Connection to %s failed" % url
        if data.status_code == 200:
            try:
                return etree.fromstring(data.text)
            except Exception as e:
                return json.loads(data.text)
        else:
            print "HTTP error code: %d" % response.status_code
        return None

    # end get_url_http

    @staticmethod
    def get_trace_buffer_names(ip, port):
        url = 'http://%s:%s/Snh_SandeshTraceBufferListRequest?' % (ip, port)
        resp = TraceUtils.get_url_http(url)
        trace_buf_names = []
        xpath = '/SandeshTraceBufferListResponse'

        try:
            tr = EtreeToDict(xpath).get_all_entry(resp)
            records = tr['trace_buffer_list']
            for rec in records:
                trace_buf_names.append(rec['trace_buf_name'])
        except Exception as e:
            self.logger.warn(
                "Got exception in get_trace_buffer_list as : %s" % (e))
        finally:
            return trace_buf_names
    # end tace_buffer_names

    @staticmethod
    def get_trace_buffer(ip, port, buffer_name=None, file_name=None, op_ip=None, nodename=None, module=None):
        '''Get traces buffers from intropsect
        '''
        buf_list = []
        txt = []
        host = socket.gethostbyaddr(ip)[0]

        if not (op_ip and nodename and module):
            print 'If traces to be sent to the database all 3 arguments - opserver_ip,node_name and module must be provided'
            return

        try:
            os.makedirs('/var/log/contrail/traces')
        except OSError:
            pass

        if buffer_name:
            buf_list.append(buffer_name)
        else:
            buf_list = TraceUtils.get_trace_buffer_names(ip, port)

        for elem in buf_list:
            url = 'http://%s:%s/Snh_SandeshTraceRequest?x=%s' % (ip,
                                                                 port, elem)
            try:
                resp = TraceUtils.get_url_http(url)
                xpath = '/SandeshTraceTextResponse'
                text = EtreeToDict(xpath).get_all_entry(resp)
                if not file_name:
                    filename = '/var/log/contrail/traces/%s_%s_traces.log' % (host, elem)
                else:
                    filename = '/var/log/contrail/traces/%s' % file_name
                for el in text['traces']:
                    with open(filename, "a+") as f:
                        f.write(el + '\n')
                print "Saved %s traces to %s" % (elem, filename)
            except Exception as e:
                print "While saving %s trace ,got exception from get_trace_buffer as %s" % (elem, e)
            if op_ip:
                try:
                    url1 = 'http://%s:8081/analytics/send-tracebuffer/%s/%s/%s' % (op_ip,
                                                                                   nodename, module, elem)
                    resp1 = TraceUtils.get_url_http(url1)
                    if (resp1['status'] == 'pass'):
                        print 'Traces saved to database'
                    else:
                        print 'Traces could not be saved to database'

                except Exception as e:
                    print 'Traces could not be saved to database'
                    print 'Got exception as %s' % e

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


class EtreeToDict(object):

    """Converts the xml etree to dictionary/list of dictionary."""

    def __init__(self, xpath):
        self.xpath = xpath
        self.xml_list = ['policy-rule']

    def _handle_list(self, elems):
        """Handles the list object in etree."""
        a_list = []
        for elem in elems.getchildren():
            rval = self._get_one(elem, a_list)
            if 'element' in rval.keys():
                a_list.append(rval['element'])
            elif 'list' in rval.keys():
                a_list.append(rval['list'])
            else:
                a_list.append(rval)

        if not a_list:
            return None
        return a_list

    def _get_one(self, xp, a_list=None):
        """Recrusively looks for the entry in etree and converts to dictionary.

        Returns a dictionary.
        """
        val = {}

        child = xp.getchildren()
        if not child:
            val.update({xp.tag: xp.text})
            return val

        for elem in child:
            if elem.tag == 'list':
                val.update({xp.tag: self._handle_list(elem)})

            if elem.tag == 'data':
                # Remove CDATA; if present
                text = elem.text.replace("<![CDATA[<", "<").strip("]]>")
                nxml = etree.fromstring(text)
                rval = self._get_one(nxml, a_list)
            else:
                rval = self._get_one(elem, a_list)

            if elem.tag in self.xml_list:
                val.update({xp.tag: self._handle_list(xp)})
            if elem.tag in rval.keys():
                val.update({elem.tag: rval[elem.tag]})
            elif 'SandeshData' in elem.tag:
                val.update({xp.tag: rval})
            else:
                val.update({elem.tag: rval})
        return val

    def find_entry(self, path, match):
        """Looks for a particular entry in the etree.
    
        Returns the element looked for/None.
        """
        xp = path.xpath(self.xpath)
        f = filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return None

    def get_all_entry(self, path):
        """All entries in the etree is converted to the dictionary

        Returns the list of dictionary/didctionary.
        """
        xps = path.xpath(self.xpath)
        if not xps:
            # sometime ./xpath dosen't work; work around
            # should debug to find the root cause.
            xps = path.xpath(self.xpath.strip('.'))
        if type(xps) is not list:
            return self._get_one(xps)

        val = []
        for xp in xps:
            val.append(self._get_one(xp))
        if len(val) == 1:
            return val[0]
        return val


def main(args_str=None):
    TraceUtils(args_str)
# end main

if __name__ == "__main__":
    main()
