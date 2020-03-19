from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import *
import time

class Multicloud(BaseK8sTest):

    def overlay_ping(self, vpc_count,onprem):
        pods=list()
        pod={}
        for key,value in self.inputs.host_data.items():
            if key in self.cloud_instances:
                if value['roles']['vpc']==vpc_count:
                    if 'compute_node' in value['roles'].keys():
                        #Creating pods on cloud computes
                        spec={'containers': [{'image': 'virtualhops/ato-ubuntu:latest', 'name': 'ubuntuapp'}], 'node_selector': {'location': key }}
                        pod[key+'-pod'] = self.setup_busybox_pod(spec=spec)
                        assert pod[key+'-pod'].verify_on_setup()
                        pods.append(pod)
                    #Creating onPrem compute
                    spec={'containers': [{'image': 'virtualhops/ato-ubuntu:latest', 'name': 'ubuntuapp'}], 'node_selector': {'location': onprem }}
                    onprem_pod=self.setup_busybox_pod(spec=spec)
                    onprem_pod.verify_on_setup()
                    #Ping from onpremcompute to all cloud computes
                    for pod in pods:
                        assert onprem_pod.ping_with_certainty(pod.values()[0].pod_ip)

    def underlay_ping(self, ip, host, count='3', expectation=True ,jumboframe=None):
        """
        Underlay ping between cloud nodes from the Onprem
        """
        output = ''
        pkt_size = '-s %s' %jumboframe if jumboframe else '' 
        cmd = "ping -c %s %s %s" % (count, pkt_size, ip)
        try:
            output = run_cmd_on_server(cmd, host, 'root','c0ntrail123')
        except Exception as e:
            self.logger.exception(
                'Exception occured while trying ping from Controller')
            return False
        expected_result = ' 0% packet loss'
        result = (expected_result in output)
        if not result:
            self.logger.warn("Ping check to IP %s from controller %s failed. "
                                "Expectation: %s, Got: %s" % (ip, host,
                                                            expected_result, result ))
            return False
        else:
            self.logger.info('Ping check to IP %s from controller %s with '
                                'expectation %s passed' % (ip, host, result))
        return True
    
    def tag_verification(self, vpc_count,cloud_instances,build_tag):
        for key,value in self.inputs.host_data.items():
            if key in cloud_instances:
                #import pdb; pdb.set_trace()
                if value['roles']['vpc']==vpc_count:
                    if 'gateway_node' in value['roles'].keys():
                        self.logger.info('Tag verification for gateway {0}'.format(key))
                        tag_list = run_cmd_on_server("docker ps | awk {'print $2'} | cut -d ':' -f2 | tail -n +2", value['host_ip'], 'root', 'c0ntrail123')
                        for tag in tag_list.split('\r\n'):
                            if tag == build_tag:
                                self.logger.info('All containers have the correct build tag')
                            else:
                                assert  False , "Some containers in the gateways dont have the correct buildtag"

    def HA_flap(self, vpc_count,cloud_instances,docker):
        for key,value in self.inputs.host_data.items():
            if key in cloud_instances:
                if value['roles']['vpc']==vpc_count:
                    if 'compute_node' in value['roles'].keys():
                        ip=value['host_ip']
                    elif 'gateway_node' in value['roles'].keys():
                        vrrp_master = run_cmd_on_server("docker logs -t vrrp_vrrp_1 2>&1 | grep STATE | tail -1", value['host_ip'], 'root', 'c0ntrail123')
                        if 'MASTER' in vrrp_master:
                            if docker == 'bird_bird_1':
                                assert(self.underlay_ping(ip,self.onprem_control.values()[0]['host_ip']))
                            else:
                                self.overlay_ping(vpc_count,self.onprem_compute.keys()[0])
                            self.logger.info('{0} HA test for gateway {1}'.format(docker,key))
                            cmd=" docker ps -a | grep %s | awk {'print $7$8$9'} "%(docker)
                            dstat = run_cmd_on_server(cmd, value['host_ip'], 'root', 'c0ntrail123')
                            if 'Up' in dstat:
                                self.logger.info('{0} status for  gateway {1} is Up. Will stop it'.format(docker,key))
                                cmd=" docker stop %s "%(docker)
                                run_cmd_on_server(cmd, value['host_ip'], 'root', 'c0ntrail123')
                                time.sleep(5)
                                cmd=" docker ps -a | grep %s | awk {'print $7$8$9'} "%(docker)
                                dstat = run_cmd_on_server(cmd, value['host_ip'], 'root', 'c0ntrail123')
                                if 'Exited' in dstat:
                                    self.logger.info('{0} status for  gateway {1} is Exited'.format(docker,key))
                                    self.logger.info('Since {0} has exited, will check for VRRP flap status after few seconds'.format(docker))
                                    time.sleep(15)
                                    vrrp_master = run_cmd_on_server("docker logs -t vrrp_vrrp_1 2>&1 | grep STATE | tail -1", value['host_ip'], 'root', 'c0ntrail123')
                                    if 'BACKUP' in vrrp_master:
                                        self.logger.info('VRRP flaped due to {0} exit as expected, will check traffic and start {0} back'.format(docker))
                                        if docker == 'bird_bird_1':
                                            assert(self.underlay_ping(ip,self.onprem_control.values()[0]['host_ip']))
                                        else:
                                            self.overlay_ping(vpc_count,self.onprem_compute.keys()[0])
                                            #run_cmd_on_server("kubectl delete pods --all", self.onprem_control.values()[0]['host_ip'], 'root', 'c0ntrail123')
                                        cmd=" docker start %s "%(docker)
                                        run_cmd_on_server(cmd, value['host_ip'], 'root', 'c0ntrail123')
                                        if self.mastership_check(value['host_ip'],docker):
                                            self.logger.info('Mastership sucessfully regained')
                                        else:
                                            assert  False , "VRRP mastership not regained after a total sleep of 4 minutes"
                                    else:
                                        assert  False , "VRRP hasnt flapped even after a sleep of 15 mins"
                                else:
                                    assert  False , "Docker has not exited, please check if the command executed properly"
                            else:
                                assert  False , "Docker is not up on the gateway, the TC cant continue"
    
    #To check VRRP membership after FLAP
    @retry(delay=10, tries=24)
    def mastership_check(self,ip,docker):
        self.logger.info('Since {0} has started, checking for VRRP status in interval of 10 seconds to regain mastership'.format(docker))
        vrrp_master = run_cmd_on_server("docker logs -t vrrp_vrrp_1 2>&1 | grep STATE | tail -1", ip, 'root', 'c0ntrail123')
        return 'MASTER' in vrrp_master




                                        









                    
