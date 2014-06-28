"""Parser to parse the netperf output."""

import re


class NetPerfParser(object):

    """Parser to parse the netperf output."""

    def __init__(self, output):
        output = output.split('\r\n')
        out_put = [x for x in output if x != '']
        self.output = out_put
        self.parsed_output = {}
        self.parse()

    def parse(self):
        pattern = "\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-9\.]+)\s+([0-9\.]+)"
        match = re.search(pattern, self.output[-1])
        (self.parsed_output['recv_sock_size'],
         self.parsed_output['send_sock_size'],
         self.parsed_output['send_msg_size'],
         self.parsed_output['elapsed_time'],
         self.parsed_output['throughput']) = match.groups()

        pattern = "\s*bytes\s+bytes\s+bytes\s+secs\.\s+([0-9\^]+)bits/sec"
        match = re.search(pattern, self.output[-2])
        self.parsed_output['throughput_bits_per_sec'] = match.group(1)
        return self.parsed_output

    def get_throughput(self):
        return float(self.parsed_output['throughput'])

    def get_elapsed_time(self):
        return int(self.parsed_output['elapsed_time'])

    def get_throughput_in_bits_per_sec(self):
        return self.parsed_output['throughput_bits_per_sec']

    def get_recv_socket_size(self):
        return int(self.parsed_output['recv_sock_size'])

    def get_send_socket_size(self):
        return int(self.parsed_output['send_sock_size'])

    def get_send_message_size(self):
        return int(self.parsed_output['send_msg_size'])
