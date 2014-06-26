"parser to parse the ping output."""

import re


class PingParser(object):

    """Parser to parse the ping output."""

    def __init__(self, output):
        self.output = output
        self.parsed_output = {}
        self.parse()

    def parse(self):
        match = re.search(
            "rtt\s+(min/avg/max/mdev)\s+=\s+(\d+.\d+/\d+.\d+/\d+.\d+/\d+.\d+)", self.output)
        output_req = []
        output_req.append(match.group(1))
        output_req.append(match.group(2))
        self.parsed_output = dict(
            zip(output_req[0].split('/'), output_req[1].split('/')))

    def get_ping_latency(self):
        return self.parsed_output['avg']
