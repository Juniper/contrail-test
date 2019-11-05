from __future__ import print_function

import sys, os
import time, re
#import pdb
import sys
# Append paths to python APIs

# sys.path.append('/path/to/hltapi/library/common/ixiangpf/python') 
# sys.path.append('/path/to/ixnetwork/api/python')
#sys.path.append('c:/Program Files (x86)/Ixia/hltapi/4.95.117.44/TclScripts/lib/hltapi/library/common/ixiangpf/python')
#sys.path.append('c:/Program Files (x86)/Ixia/IxNetwork/7.40-EA/API/Python')
#sys.path.append('c:/Program Files (x86)/Ixia/IxNetwork/7.31-EA/API/Python')

sys.path.append('/root/ixia_setup_venu/ixia/PythonApi/')
sys.path.append('/root/ixia_setup_venu/ixia/library/common/ixiangpf/python')

#sys.path.append('/root/ixia_setup/lib/PythonApi/')
#sys.path.append('/root/ixia_setup/lib/PythonApi/library/common/ixiangpf/python')
#sys.path.append('/root/ixia_setup_new/ixia/ixnetwork/8.20.1063.25/lib/PythonApi/')
#sys.path.append('/root/ixia_setup_new/ixia/ixnetwork/8.20.1063.25/lib/PythonApi/library/common/ixiangpf/python')

from ixiatcl import IxiaTcl
from ixiahlt import IxiaHlt
from ixiangpf import IxiaNgpf
from ixiaerror import IxiaError

ixiatcl = IxiaTcl()
ixiahlt = IxiaHlt(ixiatcl)
ixiangpf = IxiaNgpf(ixiahlt)

configfile = sys.argv[1:]

if not configfile:
    print("qt.py <configfile>")
    sys.exit(2)

try:
	ixnHLT_errorHandler('', {})
except (NameError,):
	def ixnHLT_errorHandler(cmd, retval):
		global ixiatcl
		err = ixiatcl.tcl_error_info()
		log = retval['log']
		additional_info = '> command: %s\n> tcl errorInfo: %s\n> log: %s' % (cmd, err, log)
		raise IxiaError(IxiaError.COMMAND_FAIL, additional_info)

def printDict(obj, nested_level=0, output=sys.stdout):
    spacing = '   '
    if type(obj) == dict:
        print('%s' % ((nested_level) * spacing), file=output)
        for k, v in list(obj.items()):
            if hasattr(v, '__iter__'):
                print('%s%s:' % ((nested_level + 1) * spacing, k), file=output)
                printDict(v, nested_level + 1, output)
            else:
                print('%s%s: %s' % ((nested_level + 1) * spacing, k, v), file=output)
        print('%s' % (nested_level * spacing), file=output)
    elif type(obj) == list:
        print('%s[' % ((nested_level) * spacing), file=output)
        for v in obj:
            if hasattr(v, '__iter__'):
                printDict(v, nested_level + 1, output)
            else:
                print('%s%s' % ((nested_level + 1) * spacing, v), file=output)
        print('%s]' % ((nested_level) * spacing), file=output)
    else:
        print('%s%s' % (nested_level * spacing, obj), file=output)


chassis_ip              = '10.87.123.247'
ixnetwork_tcl_server    = '10.87.132.18'
port_list               = '4/7 4/8 4/1 4/2'


# #############################################################################
# 								CONNECT AND PORT HANDLES
# #############################################################################

print('\n\nConnect to IxNetwork Tcl Server and get port handles...\n\n')

connect_status = ixiangpf.connect(
         device                 = chassis_ip,
 	port_list              = port_list,
 	ixnetwork_tcl_server   = ixnetwork_tcl_server,
 	tcl_server             = chassis_ip,
#        config_file            = '/root/scripts/configfile',
        config_file            = configfile,
 )
if connect_status['status'] != IxiaHlt.SUCCESS:
 	ixnHLT_errorHandler('connect', connect_status)


#connect_status = ixiangpf.connect(
#	ixnetwork_tcl_server   = ixnetwork_tcl_server,
#)
#if connect_status['status'] != IxiaHlt.SUCCESS:
#	ixnHLT_errorHandler('connect', connect_status)


#############################################################################
#   ACTION - get_all_qt_handles                                             #
#############################################################################
print("get_all_qt_handles ......\n")

test_control_status = ixiangpf.test_control(
        action =        'get_all_qt_handles',
)
if test_control_status['status'] != IxiaHlt.SUCCESS:
	ixnHLT_errorHandler('test_control:  get_all_qt_handles', test_control_status)

qt_handle_list = test_control_status['qt_handle'].split()
print("QT_handles:  ", qt_handle_list)

#############################################################################
#   ACTION - qt_apply_config   - SYNC                                       #
#############################################################################
#test_handle = qt_handle_list[0]
for test_handle in qt_handle_list:
        print("QT_apply_config ", test_handle, ".... sync mode\n")
        test_control_status = ixiangpf.test_control(
                action =        'qt_apply_config',
                qt_handle =     test_handle,
        )

        if test_control_status['status'] != IxiaHlt.SUCCESS:
                ixnHLT_errorHandler('test_control: qt_apply_config', test_control_status)
        else:
                apply_status = test_control_status[test_handle]['status']
                print("Apply config status for ", test_handle, "-----> ", apply_status)

        vportList = ixiangpf.ixnet.getList("/", 'vport')
        for vport in vportList:
            ixiangpf.ixnet.execute("resetPortCpu", vport)
            time.sleep(5)
        time.sleep(20)

        print("QT_start ", test_handle, ".... sync mode\n")
        test_control_status = ixiangpf.test_control(
                action =        'qt_start',
                qt_handle =     test_handle,
        )

        if test_control_status['status'] != IxiaHlt.SUCCESS:
                ixnHLT_errorHandler('test_control: qt_start', test_control_status)
        elif test_control_status[test_handle]['status'] != IxiaHlt.SUCCESS :
                print("Failed in test_control: qt_start ", test_handle)
                try:
                        print("log -->", test_control_status[test_handle]['log'])
                except:
                        print("no log message for the qt_start failure..")
                else:
                        print(test_handle, " is Running--> ", test_control_status[test_handle]['is_running'])
                        print("Done...")

        #############################################################################
        #   Test Stats                                                              #
        #############################################################################
        print("Test Stats ....\n")

        test_stats_status = ixiangpf.test_stats(
                mode =        'qt_currently_running',
        )

        if test_stats_status['status'] != IxiaHlt.SUCCESS:
                ixnHLT_errorHandler('test_stats: qt_currently_running', test_stats_status)
                print("Currently Running: ", test_stats_status['qt_handle'])

        ### unit in seconds
        time.sleep(10)

        is_running = '1'

        while is_running == '1':
                test_stats_status = ixiangpf.test_stats(
                        mode =        'qt_running_status',
                        qt_handle = test_handle,
                )
                if test_stats_status['status'] != IxiaHlt.SUCCESS:
                        ixnHLT_errorHandler('test_stats: qt_running_status', test_stats_status)
                else:
                        is_running = test_stats_status[test_handle]['is_running']
                        print("Test is running ", test_handle, ": ", is_running)
                        if is_running == '1':
                                test_stats_status = ixiangpf.test_stats(
                                        mode =        'qt_progress',
                                        qt_handle = test_handle,
                                )
                                if test_stats_status['status'] != IxiaHlt.SUCCESS:
                                        ixnHLT_errorHandler('test_stats: qt_progress', test_stats_status)
                                print("Progress ", test_handle, ": ", test_stats_status[test_handle]['progress'])
                                time.sleep(3)

        #############################################################################
        #  Get Test Results
        #############################################################################
        test_stats_status = ixiangpf.test_stats(
                mode      = 'qt_result',
                qt_handle = test_handle,
        )
        if test_stats_status['status'] != IxiaHlt.SUCCESS:
                ixnHLT_errorHandler('test_stats: qt_result', test_stats_status)

        print("Name: ", test_stats_status[test_handle]['name'])
        print("Duration: ", test_stats_status[test_handle]['duration'])
        print("Result: ", test_stats_status[test_handle]['result'])
        print("ResultPath: ", test_stats_status[test_handle]['result_path'])

# #############################################################################
# 								CLEANUP SESSION
# #############################################################################

# cleanup_status = ixiangpf.cleanup_session(reset='1')
# if cleanup_status['status'] != IxiaHlt.SUCCESS:
# 	ixnHLT_errorHandler('cleanup_session', cleanup_status)


print('!!! TEST is FINISHED !!!')


