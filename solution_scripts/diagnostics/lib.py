def serial(func):
    def wrapper(*args,**kwargs):
        count = kwargs.pop('count', 1)
        arg_list = kwargs.pop('args_list',[])
        kwargs_list = kwargs.pop('kwargs_list',[])
        if len(arg_list) == 0 :
          arg_list = [i for i in xrange(count)] # can be used as index
        if len(kwargs_list) == 0 :
          kwargs_list = [[] for i in xrange(count)]
        print "count",count
        print "arg_list",arg_list
        print "kwarg_list",kwargs_list
        results = []
        for i in range(count):
            result = func(arg_list[i],kwargs_list[i])
            results.append(result)
        return results
    return wrapper


import string
import random
from common.contrail_test_init import ContrailTestInit
import multiprocessing as mp
from common import log_orig as logging
from common.connections import ContrailConnections
from config import Project

class ConfigScaleSetup:
    def __init__(self):

        self.ini_file= 'sanity_params.ini'
        self.log_name='tor-scale.log'
        Logger = logging.ContrailLogger(self.log_name)
        Logger.setUp()
        self.logger = Logger.logger

    def get_connection_handle(self):

        self.inputs = ContrailTestInit(self.ini_file,logger=self.logger)
        self.inputs.setUp()
        self.connections= ContrailConnections(self.inputs, self.logger)
        self.connections.get_vnc_lib_h() # will set self.vnc_lib in the object
        self.auth = self.connections.get_auth_h()

    def config_test(self):

        self.get_connection_handle()
        tenant_name = "tenant" + "".join([random.choice(string.ascii_uppercase + string.digits) for i in xrange(10)])
        project_obj = Project(self.connections)
        project_obj.create(tenant_name)

class ParallelScaleSetup():

    def __init__(self):

        config=ConfigScaleSetup()

        # Setup a list of processes that we want to run
        processes = [mp.Process(target=config.config_test) for i in xrange(100)]

        # Run processes
        for p in processes:
            p.start()

        # Exit the completed processes
        for p in processes:
            p.join()


if __name__ == "__main__":
    config=ParallelScaleSetup()




