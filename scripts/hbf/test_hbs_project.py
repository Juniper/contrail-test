from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import test
import re
import json
import time
from pprint import pprint
from tcutils.util import get_random_name
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.util import skip_because
from tcutils.util import get_random_cidr
from k8s.namespace import NamespaceFixture
from k8s.network_attachment import NetworkAttachmentFixture
from k8s.hbs import HbsFixture
from vnc_api.vnc_api import HostBasedService
from cfgm_common import exceptions
from vnc_api.gen.resource_xsd import QuotaType

class TestHbsEnabledProject(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestHbsEnabledProject, cls).setUpClass()

    def setUp(self):
        super(TestHbsEnabledProject, self).setUp()

    @classmethod
    def tearDownClass(cls):
        super(TestHbsEnabledProject, cls).tearDownClass()


    def verify_host_based_service(self, namespace_name, hbs_obj_name, enabled=True):
        correct_config = True
        project_fq_name = ['default-domain', 'k8s-%s'%(namespace_name)]
        hbs_obj = None
        if enabled:
            hbs_obj = self.vnc_lib.host_based_service_read(project_fq_name + [hbs_obj_name])
        if hbs_obj:
           self.logger.info("Host based service object configured correctly")
        else:
           self.logger.info("Host based service object not found")
           if enabled:
               correct_config =False
        vn_list = []
        tap_intf_list = []
        left_vn_name = "__%s-hbf-left__" % (hbs_obj_name)
        right_vn_name = "__%s-hbf-right__" % (hbs_obj_name)
        for compute_ip in self.inputs.compute_ips  :
            vn_list=self.agent_inspect[compute_ip].get_vna_vn_list( domain=project_fq_name[-2], project=project_fq_name[-1])['VNs']
            tap_intf_list=self.agent_inspect[compute_ip].get_vna_tap_interface()
            vn_name_list=[]
            intf_vn_name_list = []
            for i in range(len(vn_list)) :
                x=vn_list[i]['name']
                x=x.split(":")
                vn_name_list.append(x[-1])
            for i in range(len(tap_intf_list)) :
                x=tap_intf_list[i]['vn_name']
                if x:
                    x=x.split(":")
                    intf_vn_name_list.append(x[-1])
            if ((left_vn_name in  vn_name_list)
                and (right_vn_name in vn_name_list)):
                self.logger.info("Both leftvn and rightvn found in %s " %(compute_ip))
            else:
                self.logger.info("Both leftvn and rightvn not found in %s " %(compute_ip))
                if enabled:
                    correct_config =False
            if ((left_vn_name in  intf_vn_name_list)
                and (right_vn_name in intf_vn_name_list)):
                self.logger.info("Csrx launched on compute with ip %s " %(compute_ip))
            else:
                self.logger.info("Csrx not found on compute with ip %s " %(compute_ip))
                if enabled:
                    correct_config =False
        return correct_config


    @preposttest_wrapper
    def test_verify_hbf_on_multiple_projects(self):
        '''
           1) Create 3 projects with host based service enable
           2) Verify hbs object in contrail api server
           3) Verify left vn, right vn and csrx interface objects on each compute
           4) Verify disabling hbs on one namespace, with no effect on others
        '''
        namespace1_name = get_random_name("hbsnamespace")
        namespace1_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace1_name,isolation = True))
        namespace1_fix.verify_on_setup()
        hbs1_name=get_random_name("hbsobj")
        hbs1_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        hbs1_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace2_name = get_random_name("hbsnamespace")
        namespace2_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace2_name,isolation = True))
        namespace2_fix.verify_on_setup()
        hbs2_name=get_random_name("hbsobj")
        hbs2_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs2_name,
                                   namespace = namespace2_name))
        hbs2_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace2_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace2_name, hbs_obj_name=hbs2_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace3_name = get_random_name("hbsnamespace")
        namespace3_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace3_name,isolation = True))
        namespace3_fix.verify_on_setup()
        hbs3_name=get_random_name("hbsobj")
        hbs3_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs3_name,
                                   namespace = namespace3_name))
        hbs3_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace3_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace3_name, hbs_obj_name=hbs3_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        # Disable hbs on namespace1_name
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
        self.remove_from_cleanups(hbs1_fix.cleanUp)
        self.vnc_lib.host_based_service_delete(fq_name=
              ["default-domain"] +["k8s-%s"%(namespace1_name)] + [hbs1_name])
        hbs_config_disabled = self.verify_host_based_service(namespace_name=namespace1_name,
                               hbs_obj_name=hbs1_name, enabled=False)
        assert hbs_config_disabled, "Host Based Service verification failed, check logs" 
        # Again verify hbs on namespace2_name and namespace2_name
        hbs_config = self.verify_host_based_service(namespace_name=namespace2_name, hbs_obj_name=hbs2_name)
        assert hbs_config == True, "Host Based Service verification Passesd"
        hbs_config = self.verify_host_based_service(namespace_name=namespace3_name, hbs_obj_name=hbs3_name)
        assert hbs_config == True, "Host Based Service verification Passesd"
        #self.setup_csrx(namespace_name=namespace2_name, delete=True)
        #self.setup_csrx(namespace_name=namespace3_name, delete=True)

    @preposttest_wrapper
    def test_verify_hbf_on_multiple_projects_with_non_hbf_project(self):
        '''
           1) Create 3 hbs namespaces verify leftvn, right vn, hbs object and csrx
           2) Create 1 namespace without hbs, verify hbs is not enabled there
           3) Cleanup of test case should be successful deleting all hbs objects
        '''
        namespace1_name = get_random_name("hbsnamespace")
        namespace1_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace1_name,isolation = True))
        namespace1_fix.verify_on_setup()
        hbs1_name=get_random_name("hbsobj")
        hbs1_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        hbs1_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace2_name = get_random_name("hbsnamespace")
        namespace2_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace2_name,isolation = True))
        namespace2_fix.verify_on_setup()
        hbs2_name=get_random_name("hbsobj")
        hbs2_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs2_name,
                                   namespace = namespace2_name))
        hbs2_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace2_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace2_name, hbs_obj_name=hbs2_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace3_name = get_random_name("hbsnamespace")
        namespace3_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace3_name,isolation = True))
        namespace3_fix.verify_on_setup()
        hbs3_name=get_random_name("hbsobj")
        hbs3_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs3_name,
                                   namespace = namespace3_name))
        hbs3_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace3_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace3_name, hbs_obj_name=hbs3_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace4_name = get_random_name("hbsnamespace")
        namespace4_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace4_name,isolation = True))
        namespace4_fix.verify_on_setup()

        project_obj = self.vnc_lib.project_read(fq_name=['default-domain', 'k8s-%s'%(namespace4_name)])
        hbs_obj_list = project_obj.get_host_based_services()

        if hbs_obj_list:
            self.logger.error("ERROR: Host based service objects found for %s not expected" %(namespace4_name))
            assert False
        else:
            self.logger.info("INFO: Host based service object not found for %s as expected" %(namespace4_name))
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
        #self.setup_csrx(namespace_name=namespace2_name, delete=True)
        #self.setup_csrx(namespace_name=namespace3_name, delete=True)

    @preposttest_wrapper
    def test_verify_hbsflag_toggle_with_multiple_projects_with_non_hbf_project(self):
        '''
           1) Create 3 projects with host based service enable
           2) Verify hbs object in contrail api server
           3) Verify left vn, right vn and csrx interface objects on each compute
           4) Verify disabling hbs on one namespace, with no effect on others
           5) Re enable hbs on namespace from step 4 , verify hbs on all namespaces
        '''
        namespace1_name = get_random_name("hbsnamespace")
        namespace1_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace1_name,isolation = True))
        namespace1_fix.verify_on_setup()
        hbs1_name=get_random_name("hbsobj")
        hbs1_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        hbs1_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace2_name = get_random_name("hbsnamespace")
        namespace2_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace2_name,isolation = True))
        namespace2_fix.verify_on_setup()
        hbs2_name=get_random_name("hbsobj")
        hbs2_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs2_name,
                                   namespace = namespace2_name))
        hbs2_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace2_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace2_name, hbs_obj_name=hbs2_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        namespace3_name = get_random_name("hbsnamespace")
        namespace3_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace3_name,isolation = True))
        namespace3_fix.verify_on_setup()
        hbs3_name=get_random_name("hbsobj")
        hbs3_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs3_name,
                                   namespace = namespace3_name))
        hbs3_fix.verify_on_setup()
        #self.setup_csrx(namespace_name=namespace3_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace3_name, hbs_obj_name=hbs3_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        # Disable hbs on namespace1_name
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
        self.remove_from_cleanups(hbs1_fix.cleanUp)
        self.vnc_lib.host_based_service_delete(fq_name=
             ["default-domain"] +["k8s-%s" %(namespace1_name)] + [hbs1_name])
        hbs_config_disabled = self.verify_host_based_service(namespace_name=namespace1_name,
                               hbs_obj_name=hbs1_name, enabled=False)
        assert hbs_config_disabled, "Host Based Service verification failed, check logs"
        # Again verify hbs on namespace2_name and namespace3_name
        hbs_config = self.verify_host_based_service(namespace_name=namespace2_name, hbs_obj_name=hbs2_name)
        assert hbs_config == True, "Host Based Service verification Passesd"
        hbs_config = self.verify_host_based_service(namespace_name=namespace3_name, hbs_obj_name=hbs3_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        # Enable hbs on namespace1_name
        hbs_enable = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        hbs_enable.verify_on_setup()

        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
        #self.setup_csrx(namespace_name=namespace2_name, delete=True)
        #self.setup_csrx(namespace_name=namespace3_name, delete=True)

    @preposttest_wrapper
    def test_verify_quota_limit_for_host_based_service(self):
        '''
           1) Create a namespace, attach a hbs object to it quota is 1 here.
           2) Try adding one more hbs object to namspace, expect failure.
           3) Increase hbs quota to 3 and add 2 hbs objects, verfiy hbs
           4) Cleanup should delete namespace.
        '''
        namespace1_name = get_random_name("hbsnamespace")
        namespace1_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace1_name,isolation = True))
        namespace1_fix.verify_on_setup()
        hbs1_name=get_random_name("hbsobj")
        hbs1_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        project_obj = self.vnc_lib.project_read(fq_name=['default-domain', 'k8s-%s'%(namespace1_name)])
        hbs_obj = HostBasedService(get_random_name("hbs_quota"), parent_obj=project_obj)
        try:
            self.vnc_lib.host_based_service_create(hbs_obj)
        except Exception as e:
            self.logger.info("hbs create failed %s" %(e))
        #project_obj.set_quota(QuotaType(host_based_service='3'))
        #self.vnc_lib.project_update(project_obj)
        #hbs2_name=get_random_name("hbsobj")
        #hbs2_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs2_name,
        #                           namespace = namespace1_name))
        #self.setup_csrx(namespace_name=namespace1_name)
        #hbs_config = self.verify_host_based_service(namespace_name=namespace1_name,
        # hbs_obj_name=hbs2_name)
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
        #hbs3_name=get_random_name("hbsobj")
        #hbs3_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs3_name,
        #                           namespace = namespace1_name))
        #self.setup_csrx(namespace_name=namespace1_name) 
        #hbs_config = self.verify_host_based_service(namespace_name=namespace1_name,
        #hbs_obj_name=hbs3_name)

        #self.setup_csrx(namespace_name=namespace1_name, delete=True)

    @preposttest_wrapper
    def test_hbs_with_hbf_type_label(self):
        '''
           1. Create hbs object in an namespace and verify it on node with label hbf
           2. Remove hbf label from compute node, see hbs object is removed from node
           3. Label the compute node again with hbf label, verify hbs object on the compute
           4. cleanup of hbs object and namespace should succeed
        '''
        namespace1_name = get_random_name("hbsnamespace")
        namespace1_fix = self.useFixture(NamespaceFixture(connections=self.connections,
                                         name=namespace1_name,isolation = True))
        namespace1_fix.verify_on_setup()
        hbs1_name=get_random_name("hbsobj")
        hbs1_fix = self.useFixture(HbsFixture(connections=self.connections, name=hbs1_name,
                                   namespace = namespace1_name))
        #self.setup_csrx(namespace_name=namespace1_name)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"

        #Remove hbf label form compute zero
        remove_label = "kubectl label --overwrite node %s type=" %(self.inputs.compute_names[0])
        output = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip, remove_label)
        time.sleep(60)
        project_fq_name = ['default-domain', 'k8s-%s'%(namespace1_name)]
        # csrx interfaces are deleted from compute zero, along with left and right vns
        vn_list=self.agent_inspect[self.inputs.compute_ips[0]].get_vna_vn_list(
                           domain=project_fq_name[-2], project=project_fq_name[-1])['VNs']
        vn_name_list=[]
        for i in range(len(vn_list)) :
            x=vn_list[i]['name']
            x=x.split(":")
            vn_name_list.append(x[-1])
        leftvn_name = "__%s-hbf-left__" %(hbs1_name)
        right_vn_name = "__%s-hbf-right__" %(hbs1_name)
        if ( (leftvn_name not in vn_name_list) and
              (right_vn_name not in vn_name_list) ):
            self.logger.info("Hbs interface and vn deleted from compute")
        else:
            self.logger.error("Hbs virtual networks not deleted from compute")
            assert False

        # Restore hbf label on comput zero
        add_label = "kubectl label --overwrite node %s type=hbf" %(self.inputs.compute_names[0])
        output = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip, add_label)
        time.sleep(60)
        hbs_config = self.verify_host_based_service(namespace_name=namespace1_name, hbs_obj_name=hbs1_name)
        assert hbs_config == True, "Host Based Service verification Passesd"
        #self.setup_csrx(namespace_name=namespace1_name, delete=True)
