import time
from multiprocessing import TimeoutError, Pool
from copy_reg import pickle
from types import MethodType
import config

def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)

pickle(MethodType, _pickle_method, _unpickle_method)

class MultiProcess(object):
    def __init__(self, timeout=600, max_process=30):
        self.timeout = int(timeout)
        self.pool = Pool(int(max_process))

    def create(self, target, *args, **kwargs):
        count = kwargs.pop('count', 0)
        kwargs_list = kwargs.pop('kwargs_list', None)
        args_list = kwargs.pop('args_list', None)

        n_instances = int(count) if count else 1
        if not kwargs_list:
            kwargs_list = [kwargs for i in range(n_instances)]
        if not args_list:
            args_list = [args for i in range(n_instances)]

        results = [self.pool.apply_async(target, (args_list[i],), kwargs_list[i]) for i in range(n_instances)]
        self.pool.close() # Close the pool so no more creation of new tasks

        res = list()
        for result in results:
            try:
                res.append(result.get(timeout=self.timeout))
            except TimeoutError as e:
                print 'Task overrun %d secs and timedout'%self.timeout
            except Exception as e:
                print 'Exception in task', str(e)
        self.pool.terminate() # Terminate the pool to delete the task overrun processes
        self.pool.join()

        # Figure out what to return
        if len(res) != n_instances:
            raise Exception('Exception observed in some of the processes')
        elif int(count) == 0:
            return res[0]
        return res

def pp(*args,**kwargs):
    print args,kwargs
    print "hello"
#    return multiprocessing.current_process().name
    return args[0]*2

#print MultiProcess(timeout=1).create(pp, 10)
#time.sleep(2)
#print MultiProcess(max_process=1).create(pp, 20, count=2)
#time.sleep(2)
mp = MultiProcess()
#print mp.create(pp, 20, count=3, args_list=(1,2,3,4))
print mp.create(pp, 20, count=4, args_list=[1,2,3,4], kwargs_list=[{'opt': 10}, {'opt': 11}, {'opt': 12}, {'opt': 13}])


