import sys
from lxml import etree as ET

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

def write_to_a_file(file):
    with open(file, 'w') as the_file:
        the_file.write(ET.tostring(doc))

files = sys.argv[1:] 
for file in files:
    doc = ET.parse(file)
    filter_by_tests(doc)
    change_tests_name(doc) 
    write_to_a_file(file)

