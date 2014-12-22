#!/usr/bin/python
#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

import sys
import argparse
import ConfigParser
from lxml import etree as ET

class PassParcentageCalculator(object):

    def __init__(self, args_str=None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        self.stop_on_failure() 

    # end __init__

    def get_test_count(self,doc):
        return int(self.get_attr_from_xml(doc,'tests'))
    # end get_test_count 
    
    def get_failure_count(self,doc):
        return int(self.get_attr_from_xml(doc,'failures'))
    # end get_failure_count 

    def get_attr_from_xml(self,doc,attr):
        root = doc.getroot()
        count = root.get(attr)
        return count
    # end get_attr_from_xml 

    def calculate_pass_parcentage(self,files):
        self.test_count = 0
        self.fail_count = 0
        for file in self._args.files:
            doc = ET.parse(file) 
            self.test_count += self.get_test_count(doc)
            self.fail_count += self.get_failure_count(doc)
        try:
            self.percentage=(float(self.fail_count)*100/float(self.test_count))
        except Exception as e:
            print 'Probably division by 0'
            self.percentage = 0
    # end calculate_pass_parcentage 

    def stop_on_failure(self):
        files = self._args.files
        self.calculate_pass_parcentage(files)        
        if self.percentage >= int(self._args.threshold):
            print 'Failed tests %s percent corssed the expected limit %s percent'%(str(self.percentage),str(self._args.threshold))
            sys.exit(1) 
        else:
            print 'Failures within limit %s percent'%(str(self._args.threshold))
            sys.exit(0)
    # end stop_on_failure 
    
    def _parse_args(self, args_str):
        '''
        Eg. python stop_on_fail.py 
                                        --files result.xml
                                        --threshold 12
        '''
        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        defaults = {
            'files': 'result.xml',
            'threshold': '12',
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            defaults.update(dict(config.items("DEFAULTS")))

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
        parser.set_defaults(**defaults)

        parser.add_argument(
            "--files",nargs='+' 
                ,help="Files to be checked for test failed counts")
        parser.add_argument("--threshold", help="Percentage of tests expected to be failed")

        self._args = parser.parse_args(remaining_argv)

    # end _parse_args

# end class PassParcentageCalculator


def main(args_str=None):
    PassParcentageCalculator(args_str)
# end main

if __name__ == "__main__":
    main()
