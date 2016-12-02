# Converts log files(typically in contrail-test/logs/ folder) 
# to css-based html files
# 
# This is so that failure points (i.e. at 'END TEST') can be 
# hash-tagged
#
import re
import os
import sys
import glob

css_file = 'txtsyle.css'
def write_html_file(filename):
    html_filename = '%s.html' % (filename.split('.')[0])
    html_fh = open(html_filename, 'w')
    html_fh.write('<link href="%s" rel="stylesheet" type="text/css" />' % (css_file))

    log_fh = open(filename, 'r')
    for line in log_fh.readlines():
        if 'END TEST' in line:
            testcase = re.match(r'.*END TEST : (.*) :', line).group(1)
            html_fh.write('<div id=%s>' % (testcase))
            html_fh.write(line)
            html_fh.write('</div>')
        else:
            html_fh.write(line)
    # end for
    html_fh.close()

def create_css_file(logdir):
    filename = '%s/%s' % (logdir, css_file)
    css_fh = open(filename, 'w')
    css_fh.write(
'''html, body {font-family:Courier, Arial, sans-serif ;white-space: pre-line;}
''')
    css_fh.close()

logdir = sys.argv[1]
skip_files = ['introspect.log']
for filename in glob.glob('%s/*.log' % (logdir)):
    if filename in skip_files:
        continue
    print filename
    create_css_file(logdir)
    write_html_file(filename)


