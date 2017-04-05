import os
import re
import sys
import json
import argparse
import platform
import datetime
import logging

logging.getLogger('paramiko.transport').setLevel(logging.WARN)

datetime_formats = ['%Y-%m-%d %H:%M:%S',
                    '%a %b %d %H:%M:%S %Y']
TB_format1 = 'Traceback (most recent call last)'
SKIP_FILES = ['ifmap', '.swp', 'traceback']
MAX_BTS = 1000


class BTTracker:
    '''Search for tracebacks in /var/log/contrail

    path: Optional Folder to save the collected traceback data
    log_file_prefix: Optional prefix for log file names
    ignore_tbs_input_file: path of file which has ignorable bts

    search() returns a list of dicts of format
    [ {
        'file' : '/var/log/contrail/nova-console-supervisor-stdout.log',
        'exception_name' : 'DBConnectionError',
        'exception_text' : <Full Traceback>,
        'timestamp' : timestamp of exception (datetime object),
        'line_num'  : Line number in file
     },
     ...
    ]

    'file' key would have 'contrail-api-0-stdout.log' even if the filename is
    contrail-api-0-stdout.log.1 . This is so that multiple invocations of
    search() can be used to get only the newer exceptions

    Also creates tracebacks.log, ignored_tracebacks.log,
        traceback_parse_failures.log with suitable suffixes

    '''

    def __init__(self, path='.', log_file_prefix='',
                 ignore_tbs_input_file=None):
        self.folder = '/var/log/contrail'
        hostname = platform.uname()[1]
        path = os.path.abspath(path)
        if log_file_prefix:
            log_file_prefix = log_file_prefix + '-'
        self.ignored_tb_file = '%s/%s-%signored_tracebacks.log' % (path,
                                                                   hostname, log_file_prefix)
        self.tb_file = '%s/%s-%stracebacks.log' % (path,
                                                   hostname, log_file_prefix)
        self.parse_failure_file = '%s/%s-%straceback_parse_failures.log' % (path,
                                                                            hostname, log_file_prefix)

        self.ignore_tbs_input_file = ignore_tbs_input_file
        self.ignore_errors = {}
        if ignore_tbs_input_file:
            self._read_ignore_tbs_input_file()

        self._remove_result_files()
        print 'Traceback details will be in %s' % (self.tb_file)
        print 'Ignored Traceback details will be in %s' % (self.ignored_tb_file)
        print 'Traceback parse errors will be in %s' % (self.parse_failure_file)

    def _read_ignore_tbs_input_file(self):
        if not self.ignore_tbs_input_file:
            return
        try:
            with open(self.ignore_tbs_input_file, 'r') as f_h:
                text = f_h.read()
                self.ignore_errors = json.loads(text)
        except IOError:
            pass

    # end _read_ignore_tbs_input_file

    def _remove_result_files(self):
        result_files = [self.ignored_tb_file, self.tb_file,
                        self.parse_failure_file]
        for f in result_files:
            try:
                os.remove(f)
            except OSError:
                pass
    # end _remove_result_files

    def _get_next_file(self):
        for dirname, dirs, files in os.walk(self.folder):
            for filename in files:
                if '.log' in filename or filename.endswith('.err'):
                    should_skip = False
                    for x in SKIP_FILES:
                        if x in filename:
                            should_skip = True
                            break
                    if not should_skip:
                        path = os.path.join(dirname, filename)
                        yield path
    # end _get_next_file

    def _get_tb_end_line(self, lines, tb_char_index, line_num):
        i = line_num + 1
        while i <= len(lines):
            if lines[i][tb_char_index] == ' ':
                i += 1
                continue
            else:
                # We have reached the last line of the tb
                tb_end_line_num = i
                exception_name = lines[i][tb_char_index:].split()[0]
                exception_name = re.match(r'(.*\w)', exception_name).group()
                break
        # end while
        return (exception_name, i + 1)
    # end _get_tb_end_line

    def is_date_time_str(self, string):
        for x in datetime_formats:
            try:
                if datetime.datetime.strptime(string.strip(), x):
                    return True
            except ValueError:
                pass
        return False
    # end is_date_time_str

    def parse_date_time_str(self, string):
        for x in datetime_formats:
            try:
                return datetime.datetime.strptime(string.strip(), x)
            except ValueError:
                pass
        # Unable to parse date
        raise ValueError
    # end parse_date_time_str

    def file_write(self, filename, tb_data, mode='a'):
        with open(filename, 'a') as f_h:
            f_h.write('File: %s, Line: %s\n' % (tb_data['file'],
                                                tb_data['line_num']))
            f_h.write('Error: %s, Timestamp: %s\n' % (
                tb_data['exception_name'], tb_data['timestamp']))
            text = ''.join(tb_data['exception_text'])
            f_h.write('Details:\n %s' % (text))
            f_h.write('-' * 80 + '\n')
    # end file_write

    def tb_parse_error(self, f, lines, line_num):
        '''
        Tracebacks which could not be easily parsed
        Ex : Missing log timestamps
        '''
        with open(self.parse_failure_file, 'a') as f_h:
            f_h.write('File: %s, Line: %s\n' % (f, line_num))
            text = ''.join(lines[line_num:line_num + 10])
            f_h.write('%s...\n...\n' % (text))
            f_h.write('-' * 80 + '\n')
    # end tb_parse_error

    def _get_tb_details_format_1(self, lines, line_num, file_name):
        '''
        For cgitb backtraces
        '''
        tb_string_line = lines[line_num]
        i = line_num - 1
        exception_name = None
        ts = None
        while i >= 0:
            # Get to a string which has <class '.sldfkj.abcError'>
            if (('<class \'' in lines[i] and '\'>' in lines[i]) or
                ('<type \'' in lines[i] and '\'>' in lines[i])) and \
                    lines[i + 1].startswith('Python') and \
                    self.is_date_time_str(lines[i + 2]):
                # if (lines[i].startswith('<class \'') and
                # lines[i].endswith('\'>')):
                match = re.search(r'<(class|type) \'(.*)\'>', lines[i])
                ts = None
                if match:
                    exception_name = match.group(2)
                    ts = self.parse_date_time_str(lines[i + 2])
                    tb_char_index = 0
                else:
                    # Timestamp could in that line itself
                    match = re.match(
                        r'(.*?) (.*?) (.*?).*?<(class|type) \'(.*)\'>', lines[i])
                    if match:
                        exception_name = match.group(5)
                        ts_str = '%s %s %s' % (match.group(1),
                                               match.group(2),
                                               match.group(3))
                        if self.is_date_time_str(ts_str):
                            ts = self.parse_date_time_str(ts_str)
                        else:
                            i -= 1
                            continue
                        tb_char_index = lines[line_num].index('Traceback')
                # endif
                if ts:
                    (ignore, tb_end_line_num) = self._get_tb_end_line(lines,
                                                                      tb_char_index,
                                                                      line_num)
                    return (exception_name, ts, i, tb_end_line_num)
            # end if
            i -= 1
        # end while
        self.tb_parse_error(file_name, lines, line_num)
        return (None, None, None, None)
    # end _get_tb_details_format_1

    def _get_tb_details_format_2(self, lines, line_num, file_name):
        '''
        Regular backtraces not logged using cgitb module
        '''
        exception_name = None
        ts = None
        tb_char_index = lines[line_num].index('Traceback')
        match = re.match(r'(.*?) (.*?) .*?Traceback', lines[line_num])
        if match:
            date_str = '%s %s' % (match.group(1), match.group(2))
        else:
            self.tb_parse_error(file_name, lines, line_num)
            return (None, None, None)

        if self.is_date_time_str(date_str):
            ts = self.parse_date_time_str(date_str)
            (exception_name, tb_end_line_num) = self._get_tb_end_line(lines,
                                                                      tb_char_index,
                                                                      line_num)
        else:
            self.tb_parse_error(file_name, lines, line_num)
            return (None, None, None)
        if not (exception_name and ts and tb_char_index):
            self.tb_parse_error(file_name, lines, line_num)
            return (None, None, None)
        return (exception_name, ts, tb_end_line_num)
    # end _get_tb_details_format_2

    def can_be_ignored(self, entry):
        if not self.ignore_errors:
            return False
        ignore = True
        for item in self.ignore_errors:
            f = item.get('file')
            if f and f not in entry['file']:
                ignore = False
            exception_name = item.get('exception_name')
            if exception_name and exception_name not in entry['exception_name']:
                ignore = False
            exception_text = item.get('exception_text')
            if exception_text:
                match = any(exception_text in x for x in entry[
                            'exception_text'])
                if not match:
                    ignore = False
        return ignore
    # end can_be_ignored

    def search(self):
        result = []
        for f in self._get_next_file():
            with open(f) as f_h:
                lines = f_h.readlines()
            for i in range(0, len(lines)):
                ts = None
                line = lines[i]
                if line.startswith(TB_format1):
                    (exception_name, ts, start_index, end_index) = \
                        self._get_tb_details_format_1(lines, i, f)
                elif TB_format1 in line:
                    start_index = i
                    (exception_name, ts, end_index) = \
                        self._get_tb_details_format_2(lines, i, f)
                if ts:
                    file_prefix = re.match(r'(.*.log).*', f).group(1)
                    entry = {'file': file_prefix,
                             'line_num': i,
                             'timestamp': ts,
                             'exception_name': exception_name,
                             'exception_text': lines[start_index:end_index]
                             }
                    if not self.can_be_ignored(entry):
                        result.append(entry)
                        self.file_write(self.tb_file, entry)
                    else:
                        self.file_write(self.ignored_tb_file, entry)
                    if len(result) > MAX_BTS:
                        print 'Too many backtraces...giving up'
                        sys.exit()
        print 'Done looking for tracebacks'
        return result
    # end search

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description='Search for tracebacks in /var/log/contrail')
    ap.add_argument('-p', '--path', type=str,
                    help='Optional Folder to save the collected traceback data ',
                    default='.')
    ap.add_argument('-l', '--log_file_prefix', type=str,
                    help='Optional prefix for log file names',
                    default='')
    ap.add_argument('-i', '--ignore_tbs_input_file', type=str,
                    help='path of file which has ignorable bts',
                    default='Same location as this script')
    args = ap.parse_args()
    btt = BTTracker(args.path, args.log_file_prefix,
                    args.ignore_tbs_input_file)
    result = btt.search()
