""" Module wrrapers that can be used in the tests."""

import traceback, os
from functools import wraps
from testtools.testcase import TestSkipped
import cgitb
import cStringIO
from datetime import datetime
from tcutils.util import v4OnlyTestException

from cores import *

def detailed_traceback():
    buf = cStringIO.StringIO()
    cgitb.Hook(format="text", file=buf).handle(sys.exc_info())
    tb_txt = buf.getvalue()
    buf.close()
    return tb_txt

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
        # if 'ci_image' in os.environ.keys():
        #     if os.environ['stop_execution_flag'] == 'set':
        #         assert False, "test failed skipping further tests. Refer to the logs for further analysis"
        doc = function.__doc__
        if doc:
            log.info('TEST DESCRIPTION : %s', doc)
        errmsg = []
        nodes = get_node_ips(self.inputs)
        initial_cores = get_cores(self.inputs)
        if initial_cores:
            log.warn("Test is running with cores: %s", initial_cores)

        initial_crashes = get_service_crashes(self.inputs)
        if initial_crashes:
            log.warn("Test is running with crashes: %s", initial_crashes)

        testfail = None
        testskip = None
        try:
            # check state of the connections.
            if not self.inputs.verify_control_connection(
                    connections=self.connections):
                log.warn("Pre-Test validation failed.."
                         " Skipping test %s" % (function.__name__))
      #WA for bug 1362020 
      #          assert False, "Test did not run since Pre-Test validation failed\
      #                         due to BGP/XMPP connection issue"

      #      else:
            result = None
            (test_valid, reason) = self.is_test_applicable()
            if not test_valid:
                raise self.skipTest(reason) 
            result = function(self, *args, **kwargs)
        except KeyboardInterrupt:
            raise
        except (TestSkipped, v4OnlyTestException), msg:
            testskip = True
            log.info(msg)
            result = True
            raise
        except Exception, testfail:
            test_fail_trace = detailed_traceback()
            # Stop the test in the fail state for debugging purpose
            if self.inputs.stop_on_fail:
                print test_fail_trace
                print "Failure occured; Stopping test for debugging."
                import pdb
                pdb.set_trace()
        finally:
            cleanupfail = None
            cleanup_trace = ''
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
                    cleanup_trace += '\n{0}\n{1}:\n{2}'.format(
                                                        formatted_traceback,
                                                        cet.__name__,
                                                        cei.message)

            final_cores = get_cores(self.inputs)
            cores = find_new(initial_cores, final_cores)

            final_crashes = get_service_crashes(self.inputs)
            crashes = find_new(initial_crashes, final_crashes)

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
                if 'ci_image' in os.environ.keys():
                    os.environ['stop_execution_flag'] = 'set'
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
