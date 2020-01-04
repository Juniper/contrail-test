import sys
from lxml import etree as ET
import ConfigParser

def filter_by_tests(doc, value_list = ["process-returncode"]):
    elem = doc.xpath("/testsuite/testcase[@name='process-returncode']")
    root = doc.getroot()
    tests = int(root.get('tests'))
    failures = int(root.get('failures'))
    for el in elem:
        root.remove(el)
        tests -= 1
        failures -= 1
    root.set('failures',str(failures))
    root.set('tests',str(tests))
    return doc

def change_tests_name(doc):
    root = doc.getroot()
    try:
        elem = doc.xpath("/testsuite/testcase")
        for el in elem:
            classname = el.get('classname').split('.')[-1]
            name = el.get('name')
            name = "%s.%s"%(classname,name) 
            el.set('name',name)
        el = elem[0]
        pkg = el.get('classname').split('.')[0] 
        root.set('name',pkg)
    except Exception as e:
        print 'could not change test cases names'     

def _make_url(log_location, classname, name):
    name = name.split('[')[0]
    text = '%s/%s.html#%s' % (log_location, classname.lower(), name)
    return text
# end _make_url

def add_logfile_link(doc, log_location):
    ''' For failures, add a link to the debug log file
    '''
    root = doc.getroot()
    try:
        elements = doc.xpath("/testsuite/testcase")
        for elem in elements:
            classname = elem.get('classname')
            if classname:
                classname = classname.split('.')[-1]
                name = elem.get('name').split('.')[-1]
            else:
                continue
            failures = elem.xpath('failure')
            if not failures:
                continue
            text = failures[0].text
            log_url = _make_url(log_location, classname, name)
            log_elem = ET.Element('logfile')
            log_elem.text = log_url
            elem.append(log_elem)
    except Exception,e:
        print 'Some error %s while adding log links' % (e)
# end add_logfile_link

def _get_log_location(report_file):
    config = ConfigParser.ConfigParser()
    config.read(report_file)
    log_location = config.get('Test', 'logslocation')
    return log_location

def write_to_a_file(file):
    with open(file, 'w') as the_file:
        the_file.write(ET.tostring(doc))

xmlfile = sys.argv[1]
report_file = sys.argv[2]
logs_location = _get_log_location(report_file)
doc = ET.parse(xmlfile)
filter_by_tests(doc)
change_tests_name(doc)
add_logfile_link(doc, logs_location)
write_to_a_file(xmlfile)

