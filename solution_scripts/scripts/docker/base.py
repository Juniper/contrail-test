from vm_regression.base import BaseVnVmTest

class BaseDockerTest(BaseVnVmTest):

    def create_docker(self, vn_fixture,
                      image_name='phusion-baseimage-enablesshd', 
                      *args, **kwargs):
        return self.create_vm(vn_fixture, image_name, *args, **kwargs)
