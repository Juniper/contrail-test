import os
import sys
from time import sleep
import fixtures
import testtools                                                                
import unittest
import types                                                                 
import time
trafficdir = os.path.join(os.path.dirname(__file__), '../../tcutils/pkgs/Traffic')
sys.path.append(trafficdir)
from tcutils.util import retry
from tcutils.commands import ssh
from traffic.core.stream import Stream
from traffic.core.profile import StandardProfile, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host, Sender, Receiver
from common.servicechain.config import ConfigSvcChain

class BASEDCI():


    def config_dci(self, lr1, lr2):
        dci_obj = self.vnc_lib.data_center_interconnect()
        dci_obj.set_left_lr(lr1)
        dci_obj.set_right_lr(lr2)
        self.vnc_lib.data_center_interconnect_update(dci_obj)
