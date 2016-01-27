from fabric.api import env
from tcutils.poc import Call

env.test_vn_add_delete_params = {
    "TestSet1": Call(vn_name="vn10", vn_subnets=['22.1.1.0/24']),
    "TestSet2": Call(vn_name="vn20", vn_subnets=['20.1.1.0/24'])}
