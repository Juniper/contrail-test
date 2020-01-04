#
# OpServer Utils
#
# Utility functions for Operational State Server for VNC
#
# Created by Megh Bhatt on 03/04/2013
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
try:
    from pysandesh.gen_py.sandesh.ttypes import SandeshType
except:
    class SandeshType(object):
        SYSTEM = 1
        TRACE = 4


def enum(**enums):
    return type('Enum', (), enums)
# end enum


class OpServerUtils(object):

    TIME_FORMAT_STR = '%Y %b %d %H:%M:%S.%f'
    DEFAULT_TIME_DELTA = 10 * 60 * 1000000  # 10 minutes in microseconds
    USECS_IN_SEC = 1000 * 1000
    OBJECT_ID = 'ObjectId'

    POST_HEADERS = {'Content-type':
                    'application/json; charset="UTF-8"', 'Expect': '202-accepted'}

    @staticmethod
    def utc_timestamp_usec():
        epoch = datetime.datetime.utcfromtimestamp(0)
        now = datetime.datetime.utcnow()
        delta = now - epoch
        return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)
    # end utc_timestamp_usec

    @staticmethod
    def get_start_end_time(start_time, end_time):
        if start_time == None and end_time == None:
            end_time = OpServerUtils.utc_timestamp_usec()
            start_time = end_time - OpServerUtils.DEFAULT_TIME_DELTA
        elif start_time == None and end_time != None:
            start_time = end_time - OpServerUtils.DEFAULT_TIME_DELTA
        elif start_time != None and end_time == None:
            end_time = start_time + OpServerUtils.DEFAULT_TIME_DELTA
        return start_time, end_time
    # end get_start_end_time

    @staticmethod
    def post_url_http(url, params, token):
        DEFAULT_HEADERS = {'Content-type': 'application/json; charset="UTF-8"','Expect': '202-accepted'}
        headers = DEFAULT_HEADERS.copy()
        if token:
            headers['X-AUTH-TOKEN'] = token['X-AUTH-TOKEN']
        try:
            print 'request version : %s'%(pkg_resources.get_distribution("requests").version[0])
            if int(pkg_resources.get_distribution("requests").version[0]) >= 1:
                response = requests.post(url, stream=True,
                                         data=params,
                                         headers=headers)
            else:
                response = requests.post(url, prefetch=False,
                                         data=params,
                                         headers=headers)
        except requests.exceptions.ConnectionError, e:
            print "Connection to %s failed" % url
            return None
        if response.status_code in [202 , 200]:
            return response.text
        else:
            print "HTTP error code: %d" % response.status_code
        return None
    # end post_url_http

    @staticmethod
    def get_url_http(url, headers=None):
        data = {}
        try:
            if int(pkg_resources.get_distribution("requests").version[0]) >= 1:
                data = requests.get(url, stream=True, headers=headers)
            else:
                data = requests.get(url, prefetch=False, headers=headers)
        except requests.exceptions.ConnectionError, e:
            print "Connection to %s failed" % url

        return data
    # end get_url_http

    @staticmethod
    def parse_query_result(result):
        done = False
        resit = result.iter_lines()
        while not done:
            try:
                ln = resit.next()
                if ln == '{"value": [':
                    continue
                if ln == ']}':
                    done = True
                    continue
                if ln[0] == ',':
                    out_line = '[ {} ' + ln + ' ]'
                else:
                    out_line = '[ {} , ' + ln + ' ]'

                out_list = json.loads(out_line)
                out_list.pop(0)
                for i in out_list:
                    yield i
            except Exception as e:
                print "Error parsing %s results: %s" % (ln, str(e))
        return
    # end parse_query_result

    @staticmethod
    def get_query_result(opserver_ip, opserver_port, qid, headers):
        while True:
            url = OpServerUtils.opserver_query_url(
                opserver_ip, opserver_port) + '/' + qid
            resp = OpServerUtils.get_url_http(url, headers=headers)
            if resp.status_code != 200:
                yield {}
                return
            status = json.loads(resp.text)
            if status['progress'] != 100:
                gevent.sleep(0.5)
                continue
            else:
                for chunk in status['chunks']:
                    url = OpServerUtils.opserver_url(
                        opserver_ip, opserver_port) + chunk['href']
                    resp = OpServerUtils.get_url_http(url, headers=headers)
                    if resp.status_code != 200:
                        yield {}
                    else:
                        for result in OpServerUtils.parse_query_result(resp):
                            yield result
                return
    # end get_query_result

    @staticmethod
    def convert_to_time_delta(time_str):
        num = int(time_str[:-1])
        if time_str.endswith('s'):
            return datetime.timedelta(seconds=num)
        elif time_str.endswith('m'):
            return datetime.timedelta(minutes=num)
        elif time_str.endswith('h'):
            return datetime.timedelta(hours=num)
        elif time_str.endswith('d'):
            return datetime.timedelta(days=num)
    # end convert_to_time_delta

    @staticmethod
    def convert_to_utc_timestamp_usec(time_str):
        # First try datetime.datetime.strptime format
        try:
            dt = datetime.datetime.strptime(
                time_str, OpServerUtils.TIME_FORMAT_STR)
        except ValueError:
            # Try now-+ format
            if time_str == 'now':
                return OpServerUtils.utc_timestamp_usec()
            else:
                # Handle now-/+1h format
                if time_str.startswith('now'):
                    td = OpServerUtils.convert_to_time_delta(
                        time_str[len('now'):])
                else:
                    # Handle -/+1h format
                    td = OpServerUtils.convert_to_time_delta(time_str)

                utc_tstamp_usec = OpServerUtils.utc_timestamp_usec()
                return utc_tstamp_usec + ((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6))
        else:
            return int(time.mktime(dt.timetuple()) * 10 ** 6)
    # end convert_to_utc_timestamp_usec

    @staticmethod
    def opserver_url(ip, port):
        return "http://" + ip + ":" + port
    # end opserver_url

    @staticmethod
    def opserver_query_url(opserver_ip, opserver_port):
        return "http://" + opserver_ip + ":" + opserver_port + "/analytics/query"
    # end opserver_query_url
    
    @staticmethod
    def opserver_operation_url(opserver_ip, opserver_port):
        return "http://" + opserver_ip + ":" + opserver_port + "/analytics/operation"
    # end opserver_operation_url
    
    @staticmethod
    def opserver_db_purge_url(opserver_ip, opserver_port):
        operation_url = OpServerUtils.opserver_operation_url(opserver_ip, opserver_port)
        return "%s/database-purge"%operation_url
    # end opserver_db_purge_url

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
        return OpServerUtils._data_dict_to_str(data_dict, sandesh_type)
    # end messages_data_dict_to_str

    @staticmethod
    def _data_dict_to_str(data_dict, sandesh_type):
        data_str = None
        for key, value in data_dict.iteritems():
            # Ignore if type is sandesh
            if '@type' == key and value == 'sandesh':
                continue
            # Do not print 'file' and 'line'
            if 'file' == key or 'line' == key:
                continue
            # Confirm value is dict
            if isinstance(value, dict):
                value_dict = value
            else:
                continue

            # Handle struct, list
            if '@type' in value_dict:
                if value_dict['@type'] == 'struct':
                    for vdict_key, vdict_value in value_dict.iteritems():
                        if isinstance(vdict_value, dict):
                            if data_str == None:
                                data_str = ''
                            else:
                                data_str += ', '
                            data_str += '[' + vdict_key + ': ' + \
                                OpServerUtils._data_dict_to_str(
                                    vdict_value, sandesh_type) + ']'
                    continue
                if value_dict['@type'] == 'list':
                    if data_str == None:
                        data_str = ''
                    else:
                        data_str += ', '
                    vlist_dict = value_dict['list']
                    # Handle list of basic types
                    if 'element' in vlist_dict:
                        if not isinstance(vlist_dict['element'], list):
                            velem_list = [vlist_dict['element']]
                        else:
                            velem_list = vlist_dict['element']
                        data_str += '[' + key + ':'
                        for velem in velem_list:
                            data_str += ' ' + velem
                        data_str += ']'
                    # Handle list of complex types
                    else:
                        data_str += '[' + key + ':'
                        for vlist_key, vlist_value in vlist_dict.iteritems():
                            if isinstance(vlist_value, dict):
                                vlist_value_list = [vlist_value]
                            elif isinstance(vlist_value, list):
                                vlist_value_list = vlist_value
                            else:
                                continue
                            for vdict in vlist_value_list:
                                data_str += ' [' + \
                                    OpServerUtils._data_dict_to_str(
                                        vdict, sandesh_type) + ']'
                        data_str += ']'
                    continue
            else:
                if data_str == None:
                    data_str = ''
                else:
                    data_str += ', '
                data_str += '[' + \
                    OpServerUtils._data_dict_to_str(
                        value_dict, sandesh_type) + ']'
                continue

            if sandesh_type == SandeshType.SYSTEM or sandesh_type == SandeshType.TRACE:
                if data_str == None:
                    data_str = ''
                else:
                    data_str += ' '
                if '#text' in value_dict:
                    data_str += value_dict['#text']
                if 'element' in value_dict:
                    data_str += value_dict['element']
            else:
                if data_str == None:
                    data_str = ''
                else:
                    data_str += ', '
                if '#text' in value_dict:
                    data_str += key + ' = ' + value_dict['#text']
                elif 'element' in value_dict:
                    data_str += key + ' = ' + value_dict['element']
                else:
                    data_str += key + ' = '

        if data_str == None:
            data_str = ''
        return data_str
    # end _data_dict_to_str

    @staticmethod
    def get_query_dict(table, start_time=None, end_time=None,
                       select_fields=None,
                       where_clause="",
                       sort_fields=None, sort=None, limit=None, filter=None, dir=None, session_type=None):
#    @staticmethod
#    def get_query_dict(table, start_time = None, end_time = None,
#            select_fields = None,
#            where_clause = "",
#            sort_fields = None, sort = None, limit = None, filter = None):
        """
        This function takes in the query parameters, format appropriately and calls
        ReST API to the :mod:`opserver` to get data

        :param table: table to do the query on
        :type table: str
        :param start_time: start_time of the query's timeperiod
        :type start_time: int
        :param end_time: end_time of the query's timeperiod
        :type end_time: int
        :param select_fields: list of columns to be returned in the final result
        :type select_fields: list of str
        :param where_clause: list of match conditions for the query
        :type where_clause: list of match, which is a pair of str ANDed
        :dir:int
        :session_type: needs to be set to  client or server when querying session tables
        :returns: str -- dict of query request
        :raises: Error

        """

        try:
            if start_time.isdigit():
                start_time = int(start_time)
            else:
                start_time = OpServerUtils.convert_to_utc_timestamp_usec(
                    start_time)
            if end_time.isdigit():
                end_time = int(end_time)
            else:
                end_time = OpServerUtils.convert_to_utc_timestamp_usec(
                    end_time)
        except:
            print 'Incorrect start-time (%s) or end-time (%s) format' % (start_time,
                                                                         end_time)
            return None

        sf = select_fields
        lstart_time, lend_time = OpServerUtils.get_start_end_time(start_time,
                                                                  end_time)
        where = []
        for term in where_clause.split('OR'):
            term_elem = []
            for match in term.split('AND'):
                if match == '':
                    continue
                match_s = match.strip(' ()')
                match_e = match_s.split('=')
                match_e[0] = match_e[0].strip(' ()')
                match_e[1] = match_e[1].strip(' ()')
                match_v = match_e[1].split("<")

                if len(match_v) is 1:
                    if match_v[0][-1] is '*':
                        match_prefix = match_v[0][:(len(match_v[0]) - 1)]
                        print match_prefix
                        match_elem = OpServerUtils.Match(name=match_e[0],
                                                         value=match_prefix,
                                                         op=OpServerUtils.MatchOp.PREFIX)
                    else:
                        match_elem = OpServerUtils.Match(name=match_e[0],
                                                         value=match_v[0],
                                                         op=OpServerUtils.MatchOp.EQUAL)
                else:
                    match_elem = OpServerUtils.Match(name=match_e[0],
                                                     value=match_v[0],
                                                     op=OpServerUtils.MatchOp.IN_RANGE, value2=match_v[1])
                term_elem.append(match_elem.__dict__)

            if len(term_elem) == 0:
                where = None
            else:
                where.append(term_elem)

        filter_terms = []
        if filter is not None:
            for match in filter.split(','):
                match_s = match.strip(' ()')
                match_e = match_s.split('=')
                match_op = ["", ""]
                if (len(match_e) == 2):
                    match_op[0] = match_e[0].strip(' ()')
                    match_op[1] = match_e[1].strip(' ()')
                    op = OpServerUtils.MatchOp.REGEX_MATCH

                match_e = match_s.split('<')
                if (len(match_e) == 2):
                    match_op[0] = match_e[0].strip(' ()')
                    match_op[1] = match_e[1].strip(' ()')
                    op = OpServerUtils.MatchOp.LEQ

                match_e = match_s.split('>')
                if (len(match_e) == 2):
                    match_op[0] = match_e[0].strip(' ()')
                    match_op[1] = match_e[1].strip(' ()')
                    op = OpServerUtils.MatchOp.GEQ

                match_elem = OpServerUtils.Match(name=match_op[0],
                                                 value=match_op[1],
                                                 op=op)
                filter_terms.append(match_elem.__dict__)

        if len(filter_terms) == 0:
            filter_terms = None
        query_result = OpServerUtils.Query(table,
                                          start_time=lstart_time,
                                          end_time=lend_time,
                                          select_fields=sf,
                                          where=where,
                                          sort_fields=sort_fields,
                                          sort=sort,
                                          limit=limit,
                                          filter=filter_terms,
                                          dir=dir,
                                          session_type=session_type)
        return query_result.__dict__

    @staticmethod
    def get_json_body(*args,**kwargs):
        json = OpServerUtils.Json_Body(*args,**kwargs)
        return json.__dict__    
    #end get_json_body

    class Json_Body(object):
        def __init__(self,*args,**kwargs):
            self.purge_input = kwargs['purge_input']
    #end Json_Body

    class Query(object):
        table = None
        start_time = None
        end_time = None
        select_fields = None
        where = None
        sort = None
        sort_fields = None
        limit = None
        filter = None
        dir = None
        session_type = None
        def __init__(
            self, table, start_time, end_time, select_fields, where=None,
                sort_fields=None, sort=None, limit=None, filter=None, dir=None, session_type=None):
#        def __init__(self, table, start_time, end_time, select_fields, where = None,
# sort_fields = None, sort = None, limit = None, filter = None):
            self.table = table
            self.start_time = start_time
            self.end_time = end_time
            self.select_fields = select_fields
            if where is not None:
                self.where = where
            if sort_fields is not None:
                self.sort_fields = sort_fields
            if sort is not None:
                self.sort = sort
            if limit is not None:
                self.limit = limit
            if filter is not None:
                self.filter = filter
            if dir is not None:
                self.dir = dir
            if session_type is not None:
                self.session_type = session_type
            
        # end __init__

    # end class Query

    MatchOp = enum(EQUAL=1, NOT_EQUAL=2, IN_RANGE=3,
                   NOT_IN_RANGE=4, LEQ=5, GEQ=6, PREFIX=7, REGEX_MATCH=8)

    SortOp = enum(ASCENDING=1, DESCENDING=2)

    class Match(object):
        name = None
        value = None
        op = None
        value2 = None

        def __init__(self, name, value, op, value2=None):
            self.name = name
            self.value = value
            self.op = op
            self.value2 = value2
        # end __init__

    # end class Match

# end class OpServerUtils
