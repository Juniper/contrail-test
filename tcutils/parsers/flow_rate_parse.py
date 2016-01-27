"parser to parse the 'flow -r' output."""

import re
class FlowRateParser:
    "Parser to parse flow -r output"
    def __init__(self, filename):
        file=open(filename,'r')
        self.lines = file.readlines()
        self.flow_rate =[]
        self.parse()

    def parse(self):
        pattern = "Flow setup rate =\s+(-?\d+)\s+flows/sec"
        for line in self.lines:
            match = re.search(pattern, line)
            self.flow_rate.append(int(match.group(1)))

    def flowrate(self):
        flow_rate_filtered = []
        for item in self.flow_rate:
            #Removing negative and flows ceated by copy/ping metadata actions.
            if item > 100:
                flow_rate_filtered.append(item)
        flow_rate_filtered.sort()
        length = len(flow_rate_filtered)
        if length % 2 == 0:
            mid = length/2
            flow_rate = (flow_rate_filtered[mid] + flow_rate_filtered[mid-1])/2
        else:
            flow_rate = flow_rate_filtered[((length +1)/2)-1]
        return flow_rate
