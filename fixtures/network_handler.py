
class NetworkHandler():
    def __init__(self, username, password, connections, cfgm_ip ):
        self.username= username
        self.password= password
        self.cfgm_ip = cfgm_ip
        self.inputs= inputs
        self.obj=None
        self.logger= self.inputs.logger

    def create_network(self, vn_name, vn_subnets, ipam_fq_name, project_id):
        pass

    def get_vn_obj_if_present(self, vn_name =None, vn_id=None, project_id=None):
        pass

    def get_vn_id_from_obj( self, obj):
        pass

    def delete_vn(self, vn_id):
        pass

    def list_networks(self, args):
        pass

    def get_vn_id(self, vn_name):
        pass

#    def get_vn_fq_name ( self, obj):
#        pass

#end NetworkHandler
