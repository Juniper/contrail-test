from email.mime.text import MIMEText
import smtplib
import subprocess
import ConfigParser
import xml.etree.ElementTree as ET
import sys

def update_xml(config_file, xmlfile):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    build_id = config.get('Test', 'Build')
    timestamp = config.get('Test', 'timestamp')
    report_loc = config.get('Test', 'Report')
    topology = config.get('Test', 'Topology')

    result_tree = ET.parse(xmlfile)
    ts_root = result_tree.getroot()
    properties_elem = ET.Element('properties')

    try:
        logs_location = config.get('Test', 'LogsLocation')
        prop_elem = ET.Element('property')
        prop_elem.set('name','LogsLocation')
        prop_elem.set('value', logs_location)
        properties_elem.append(prop_elem)
    except ConfigParser.NoOptionError,e:
        pass
        
    prop_elem = ET.Element('property')
    prop_elem.set('name','Build') 
    prop_elem.set('value', build_id) 
    properties_elem.append(prop_elem)

    prop_elem = ET.Element('property')
    prop_elem.set('name','Report')
    prop_elem.set('value', report_loc)
    properties_elem.append(prop_elem)

    prop_elem = ET.Element('property')
    prop_elem.set('name','Topology')
    prop_elem.set('value', topology)
    properties_elem.append(prop_elem)
   
    ts_root.append(properties_elem)
    result_tree.write(xmlfile)
# end 
    
    

# end update_xml

if __name__ == "__main__":
    # accept report_details.ini, result.xml
    update_xml(sys.argv[1], sys.argv[2])
