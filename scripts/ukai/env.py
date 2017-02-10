gc_host      = "99.1.1.11"
gc_user_name = "root"
gc_user_pwd  = "c0ntrail123"
username = "admin"
password = "575EBC2EA286"
admin_tenant_name = "admin"
auth_url = "http://5.5.5.11:5000/v2.0/"
ukai_url = "http://99.1.1.11:9500/"

env_non_admin = 'export GOHAN_ENDPOINT_URL=http://99.1.1.11:9500; export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_AUTH_URL="http://99.1.1.11:5000/v2.0";'

env_admin = 'export GOHAN_ENDPOINT_URL=http://99.1.1.11:9500; export OS_USERNAME=admin; export OS_PASSWORD=575EBC2EA286; export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_TENANT_NAME=admin; export OS_AUTH_URL="http://99.1.1.11:5000/v2.0";'

env_vm =  'export GOHAN_ENDPOINT_URL=http://99.1.1.11:9500; export OS_USERNAME=admin; export OS_PASSWORD=575EBC2EA286; export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_AUTH_URL="http://99.1.1.11:5000/v2.0";'

contrail_env = 'source /etc/contrail/openstackrc;'

