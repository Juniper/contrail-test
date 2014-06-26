"""Customized HTMLTestTunner
	1. Customized for adding core count in the test report.
   Can be extended when required.
"""
import re
import sys
import datetime

from HTMLTestRunner import HTMLTestRunner, _TestResult


class ContrailTestResult(_TestResult):

    """Contrail Test Result with overrided addFailure and addError
    callback to add core count in the test report.
    """

    def __init__(self, verbosity=1):
        super(ContrailTestResult, self).__init__(verbosity)
        self.core_count = 0
        self.crash_count = 0
        self.core_list = []

    def addFailure(self, test, err):
        self.addCores(err)
        self.addCrashes(err)
        super(ContrailTestResult, self).addFailure(test, err)

    def addError(self, test, err):
        self.addCores(err)
        self.addCrashes(err)
        super(ContrailTestResult, self).addError(test, err)

    def addCores(self, err):
        """Add core count when addFailure or addError callbacks is called by
        unittest.Result.
        """
        # Change this pattern if output format in tcutils.wrapper.py is
        # changed.
        match = re.search("Cores found\(([0-9]+)\): \{([\S ]+)\}", str(err[1]))
        if match:
            self.core_count += int(match.group(1))
            core_list = match.group(2)
            core_list = re.findall(r'core.\S+.[0-9]+.\S+.[0-9]+', core_list)
            self.core_list += core_list

    def addCrashes(self, err):
        """Add crash count when addFailure or addError callbacks is called by
        unittest.Result.
        """
        # Change this pattern if output format in tcutils.wrapper.py is
        # changed.
        match = re.search("Contrail service crashed\(([0-9]+)\)", str(err[1]))
        if match:
            self.crash_count += int(match.group(1))


class ContrailHTMLTestRunner(HTMLTestRunner):

    """Contrail HTML Test runner with overrided getReportAttributes
    and run method to customize the test report.
    """

    def __init__(self, stream=sys.stdout, verbosity=1, title=None, description=None):
        super(ContrailHTMLTestRunner, self).__init__(
            stream, verbosity, title, description)

    def run(self, test):
        """Run the given test case or test suite.
        Pass customized ContrailTestResult.
        """
        result = ContrailTestResult(self.verbosity)
        test(result)
        self.stopTime = datetime.datetime.now()
        self.generateReport(test, result)
        print >>sys.stderr, '\nTime Elapsed: %s' % (
            self.stopTime - self.startTime)
        return result

    def getReportAttributes(self, result):
        """
        Return report attributes as a list of (name, value)
        along with core information.
        """
        attributes = super(ContrailHTMLTestRunner,
                           self).getReportAttributes(result)
        if not result.core_count and not result.crash_count:
            return attributes

        status = []
        for key, val in attributes:
            if key == "Status":
                attributes.remove((key, val))
                if val != 'none':
                    status.append(val)

        if result.core_count:
            status.append('Cores %s' % result.core_count)
        if result.crash_count:
            status.append('Crashes %s' % result.crash_count)
        status = ' '.join(status)
        result.core_list = ', '.join(result.core_list)
        attributes.append(('Status', status))
        attributes.append(('Cores List', result.core_list))

        return attributes
