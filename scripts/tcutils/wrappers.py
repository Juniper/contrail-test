""" Module wrrapers that can be used in the tests."""

import traceback
from functools import wraps
from testtools.testcase import TestSkipped
from datetime import datetime

from cores import *


def preposttest_wrapper(function):
    """Decorator to perform pretest and posttest validations.
    when a test is wrraped with this decorator
    1. Logs the test start with test doc string
    2. Checks connection states
    3. Collects cores/crashes before test
    4. Executes the test
    5. Collects cores/crashes after test
    6. Compares pre-cores/crashes with post-cores/crashes to decide test result.
    7. Logs the test result.
    """
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        core_count = 0
        crash_count = 0
        log = self.inputs.logger
        log.info('=' * 80)
        log.info('STARTING TEST    : %s', function.__name__)
        start_time = datetime.now().replace(microsecond=0)
        doc = function.__doc__
        if doc:
            log.info('TEST DESCRIPTION : %s', doc)
        errmsg = []
        nodes = get_node_ips(self.inputs)
        initial_cores = get_cores(nodes, self.inputs.username,
                                  self.inputs.password)
        if initial_cores:
            log.warn("Test is running with cores: %s", initial_cores)

        initial_crashes = get_service_crashes(nodes, self.inputs.username,
                                              self.inputs.password)
        if initial_crashes:
            log.warn("Test is running with crashes: %s", initial_crashes)

        # vrouter validation: i. Take snapshop of memory usage..
        vr_mem_stats = {}
        #vr_mem_stats= self.analytics_obj.get_vrouter_mem_stats()
        if vr_mem_stats != {}:
            do_mem_check = True
            log.info("vr_mem_stats: %s" % vr_mem_stats)
        else:
            do_mem_check = False
            log.error(
                "VR mem stats not available, skipping check, needs to be debugged...")
        if do_mem_check:
            vr_mem_pre_test = {}
            for i, j in vr_mem_stats.items():
                vr_mem_pre_test[i] = j
            log.info("VR memory before start of test: %s" % vr_mem_pre_test)

        # ii. take snapshot of packet drops
        #vr_drop_stats_pre_test= {}
        # for i,j in self.analytics_obj.get_vrouter_drop_stats().items():
        #    vr_drop_stats_pre_test[i]= j
        #log.info("VR drop stats before start of test: %s" %vr_drop_stats_pre_test)

        testfail = None
        testskip = None
        try:
            # check state of the connections.
            if not self.inputs.verify_control_connection(
                    connections=self.connections):
                log.warn("Pre-Test validation failed.."
                         " Skipping test %s" % (function.__name__))
                assert False, "Test did not run since Pre-Test validation failed\
                               due to BGP/XMPP connection issue"

            else:
                result = None
                result = function(self, *args, **kwargs)
        except KeyboardInterrupt:
            raise
        except TestSkipped, msg:
            testskip = True
            log.info(msg)
            result = True
        except Exception, testfail:
            et, ei, tb = sys.exc_info()
            formatted_traceback = ''.join(traceback.format_tb(tb))
            test_fail_trace = '\n{0}\n{1}:\n{2}'.format(formatted_traceback,
                                                        et.__name__, ei.message)
            # Stop the test in the fail state for debugging purpose
            if self.inputs.stop_on_fail:
                print test_fail_trace
                print "Failure occured; Stopping test for debugging."
                import pdb
                pdb.set_trace()
        finally:
            cleanupfail = None
            while self._cleanups:
                cleanup, args, kwargs = self._cleanups.pop(-1)
                try:
                    cleanup(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except Exception, cleanupfail:
                    #result.addError(self, sys.exc_info())
                    cet, cei, ctb = sys.exc_info()
                    formatted_traceback = ''.join(traceback.format_tb(ctb))
                    cleanup_trace = '\n{0}\n{1}:\n{2}'.format(formatted_traceback,
                                                              cet.__name__, cei.message)

            final_cores = get_cores(nodes, self.inputs.username,
                                    self.inputs.password)
            cores = find_new(initial_cores, final_cores)

            final_crashes = get_service_crashes(nodes, self.inputs.username,
                                                self.inputs.password)
            crashes = find_new(initial_crashes, final_crashes)

            # vrouter health check- post test
            # i> check memory, check if pre_test_mem_stats worked, if yes,
            # continue..
            if do_mem_check:
                vr_mem_stats = {}
                #vr_mem_stats= self.analytics_obj.get_vrouter_mem_stats()
                if vr_mem_stats != {}:
                    do_mem_check = True
                    log.info(
                        "vr_mem_stats: %s" % vr_mem_stats)
                else:
                    do_mem_check = False
                    log.error(
                        "VR mem stats not available, skipping check, needs to be debugged...")
            if do_mem_check:
                vr_mem_post_test = {}
                for i, j in vr_mem_stats.items():
                    vr_mem_post_test[i] = j
                log.info("VR memory after running test: %s" % vr_mem_post_test)
                vr_list = self.analytics_obj.get_vrouter_mem_stats().keys()
                # check %diff between pre & post test vm_mem stats..
                # For now raise warn if post test is 10% more than pre test..
                vr_mem_increase_pct = {}
                for i in vr_list:
                    vr_mem_increase_pct[i] = (
                        (float(vr_mem_post_test[i] - vr_mem_pre_test[i])) / float(vr_mem_pre_test[i])) * 100
                    vr_mem_increase_pct[i] = round(vr_mem_increase_pct[i], 2)
                    log.info("vr_mem_increase_pct for %s is %.2f" %
                             (i, vr_mem_increase_pct[i]))
                    if vr_mem_increase_pct[i] > 10:
                        err_msg = ("Node %s, VR Mem up more than expected after running test: %s%%, pre-test= %s,post-test=%s"
                                   % (i, vr_mem_increase_pct[i], vr_mem_pre_test[i], vr_mem_post_test[i]))
                        log.warn(err_msg)
                    if vr_mem_increase_pct[i] > 30:
                        log.error(err_msg)
                        assert False, err_msg
            # Done with vr mem check

            # ii> check for packet drops
            vr_drop_stats_post_test = {}
            # for i,j in self.analytics_obj.get_vrouter_drop_stats().items():
            #    vr_drop_stats_post_test[i]= j
            #log.info("VR drop stats after running test: %s" %vr_drop_stats_post_test)
            #vr_list= self.analytics_obj.get_vrouter_drop_stats().keys()
            # check %diff between pre & post test vm_drop_stats
            #vr_drops_increase_pct= {}
            # for i in vr_list:
            #    vr_drops_increase_pct[i]= {}
            #    for x,y in vr_drop_stats_post_test[i].items():
            #        if vr_drop_stats_pre_test[i][x] > 0:
            #            vr_drops_increase_pct[i][x]= ((float(vr_drop_stats_post_test[i][x] - vr_drop_stats_pre_test[i][x]))/float(vr_drop_stats_pre_test[i][x]))*100
            #            vr_drops_increase_pct[i][x]= round(vr_drops_increase_pct[i][x],2)
            #        else: vr_drops_increase_pct[i][x]= 0
            #        if vr_drops_increase_pct[i][x] > 0:
            #            if x not in ['ds_invalid_arp', 'ds_duplicated']:
            #                log.info ("vr drop stats increase pct for node %s, %s is %.2f" %(i, x, vr_drops_increase_pct[i][x]))
            # Done with packet drop check

            if testfail:
                log.error(test_fail_trace)
                errmsg.append("Test failed: %s" % test_fail_trace)

            if cleanupfail:
                log.error(cleanup_trace)
                errmsg.append("Cleanup failed: %s" % cleanup_trace)

            if cores:
                for node, corelist in cores.items():
                    core_count += len(corelist)
                # Preserve this msg format, it is used by
                # tcutils.contrailtestrunner
                msg = "Cores found(%s): %s" % (core_count, cores)
                log.error(msg)
                errmsg.append(msg)
            if crashes:
                for node, crashlist in crashes.items():
                    crash_count += len(crashlist)
                # Preserve this msg format, it is used by
                # tcutils.contrailtestrunner
                msg = "Contrail service crashed(%s): %s" % (
                    crash_count, crashes)
                log.error(msg)
                errmsg.append(msg)

            test_time = datetime.now().replace(microsecond=0) - start_time
            if cores == {} and crashes == {} and not testfail and \
			not cleanupfail and result is None:
                log.info("END TEST : %s : PASSED[%s]",
                         function.__name__, test_time)
                log.info('-' * 80)
            elif cores or crashes or testfail or cleanupfail or result is False:
                log.info('')
                log.info("END TEST : %s : FAILED[%s]",
                         function.__name__, test_time)
                log.info('-' * 80)
                raise TestFailed("\n ".join(errmsg))
            elif testskip:
                log.info('')
                log.info('END TEST : %s : SKIPPED[%s]',
                         function.__name__, test_time)
                log.info('-' * 80)
            else:
                log.info('')
                log.info('END TEST : %s : PASSED[%s]',
                         function.__name__, test_time)
                log.info('-' * 80)

    return wrapper
