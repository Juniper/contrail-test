""" Module wrrapers that can be used in the tests."""
from __future__ import print_function
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
import traceback, os, signal
from functools import wraps
from testtools.testcase import TestSkipped
import cgitb
import io
from datetime import datetime
from tcutils.util import v4OnlyTestException
from tcutils.test_lib.contrail_utils import check_xmpp_is_stable

from .cores import *

def detailed_traceback():
    buf = io.BytesIO() if sys.version_info[0] == 2 else io.StringIO() 
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
        initial_cores = get_cores(self.inputs)
        if initial_cores:
            log.warn("Test is running with cores: %s", initial_cores)

        initial_crashes = get_service_crashes(self.inputs)
        if initial_crashes:
            log.warn("Test is running with crashes: %s", initial_crashes)

        (flap_check_result, initial_xmpp_flaps) = check_xmpp_is_stable(
                self.inputs, self.connections)

        testfail = None
        testskip = None
        try:
            # check state of the connections.
            # Commenting below 4 lines due to discovery changes in R4.0 - Bug 1658035
            #if not self.inputs.verify_control_connection(
            #        connections=self.connections):
            #    log.warn("Pre-Test validation failed.."
            #             " Skipping test %s" % (function.__name__))
      #WA for bug 1362020 
      #          assert False, "Test did not run since Pre-Test validation failed\
      #                         due to BGP/XMPP connection issue"

      #      else:
            result = None
            (test_valid, reason) = self.is_test_applicable()
            if not test_valid:
                raise self.skipTest(reason) 
            log.info('Initial checks done. Running the testcase now')
            log.info('')
            result = function(self, *args, **kwargs)
            if self.inputs.upgrade:
                pid = os.getpid()
                log.info('UPGRADE: %s[%s]: Stopping self',
                    function.__name__, pid)
                log.info('-' * 80)
                os.kill(pid, signal.SIGSTOP)
                log.info('UPGRADE: %s[%s]: Resuming validation post upgrade',
                    function.__name__, pid)
                log.info('-' * 80)
                self.validate_post_upgrade()
        except KeyboardInterrupt:
            pass
        except (TestSkipped, v4OnlyTestException) as msg:
            testskip = True
            log.info(msg)
            result = True
            raise
        except Exception as msg:
            testfail=True
            test_fail_trace = detailed_traceback()
            # Stop the test in the fail state for debugging purpose
            if self.inputs.stop_on_fail:
                print(test_fail_trace)
                print("Failure occured; Stopping test for debugging.")
                import remote_pdb;
                remote_pdb.set_trace()
        finally:
            cleanupfail = None
            cleanup_trace = ''
            if getattr(self, 'parallel_cleanup',None):
                parallel_cleanup_list = self.parallel_cleanup()
            while self._cleanups:
                cleanup, args, kwargs = self._cleanups.pop(-1)
                try:
                    cleanup(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except Exception as cleanupfail:
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
                for node, corelist in list(cores.items()):
                    core_count += len(corelist)
                # Preserve this msg format, it is used by
                # tcutils.contrailtestrunner
                msg = "Cores found(%s): %s" % (core_count, cores)
                log.error(msg)
                errmsg.append(msg)
            if crashes:
                for node, crashlist in list(crashes.items()):
                    crash_count += len(crashlist)
                # Preserve this msg format, it is used by
                # tcutils.contrailtestrunner
                msg = "Contrail service crashed(%s): %s" % (
                    crash_count, crashes)
                log.error(msg)
                errmsg.append(msg)

            (flap_check_result, current_xmpp_flags)= check_xmpp_is_stable(
                self.inputs, self.connections, initial_xmpp_flaps)

            test_time = datetime.now().replace(microsecond=0) - start_time
            if cores == {} and crashes == {} and not testfail and \
		            not cleanupfail and (result is None or result is True) and \
                    flap_check_result and not testskip:
                log.info("END TEST : %s : PASSED[%s]",
                         function.__name__, test_time)
                log.info('-' * 80)
            elif cores or crashes or testfail or cleanupfail or \
                    result is False or not flap_check_result:
                log.info('')
                log.info("END TEST : %s : FAILED[%s]",
                         function.__name__, test_time)
                log.info('-' * 80)
                if 'ci_image' in list(os.environ.keys()):
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
