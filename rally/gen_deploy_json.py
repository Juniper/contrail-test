
'''
cat existing.json
{
    "type": "ExistingCloud",
    "auth_url": "http://example.net:5000/v2.0/",
    "region_name": "RegionOne",
    "endpoint_type": "public",
    "admin": {
        "username": "admin",
        "password": "myadminpass",
        "tenant_name": "demo"
    },
    "https_insecure": false,
    "https_cacert": ""
}
cat /etc/contrail/openstackrc
export OS_USERNAME=admin
export OS_PASSWORD=contrail123
export OS_TENANT_NAME=admin
export OS_REGION_NAME=RegionOne
export OS_AUTH_URL=http://10.87.143.105:35357/v2.0
export OS_NO_CACHE=1

'''

import json

rally_cloud={}
rally_cloud['type']="ExistingCloud"
rally_cloud['region_name']="RegionOne"
rally_cloud['endpoint_type']='public'
rally_cloud['https_insecure']=False
rally_cloud['https_cacert']=""
rally_cloud['admin']={}
with open('/etc/contrail/openstackrc', 'r') as rc:
    for line in rc.read().split('\n'):
        if 'USERNAME' in line:
            rally_cloud['admin']['username']=line.split("=")[1]
        elif 'PASSWORD' in line:
            rally_cloud['admin']['password']=line.split("=")[1]
        elif 'TENANT_NAME' in line:
            rally_cloud['admin']['tenant_name']=line.split("=")[1]
        elif 'AUTH_URL' in line:
            rally_cloud['auth_url']=line.split("=")[1]

with open('./rally/existing.json', 'w') as rc:
    rc.write(json.dumps(rally_cloud))


