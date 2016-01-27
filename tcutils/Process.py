from multiprocessing import TimeoutError, Pool
from copy_reg import pickle
import threading
import marshal
import thread
import types
import sys
from common import log_orig as logging
LOG = logging.getLogger(__name__)

def wrapper(func):
    ''' Decorator to create n tasks 
    Optional:
    :param max_process: No of concurrent processes to create to handle the tcount tasks (default 30)
    :param tcount : No of tasks to create if less than 1 run the task in the current process context (default 1)
    :param timeout : Max wait time in secs for the task to complete execution (default 600s)
    :param args_list : list of args for each task (default: same args is passed to each task)
    :param kwargs_list : list of kwargs for each task (default: same kwargs is passed to each task)
    '''
    def inner(*args, **kwargs):
        if kwargs.get('tcount', 1) > 1 and kwargs.get('max_process', 30) > 1:
            return multi_process(func, *args, **kwargs)
        else:
            kwargs.pop('tcount', None)
            kwargs.pop('max_process', None)
            return func(*args, **kwargs)
    return inner

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
pickle(types.MethodType, _pickle_method, _unpickle_method)

lock = dict()
def get_lock(key):
    global lock
    if key not in lock.keys():
        lock[key] = threading.Lock()
    return lock[key]
def _pickle_lock(lock):
    return _unpickle_lock, (lock.__hash__(),)
def _unpickle_lock(key):
    return get_lock(key)
pickle(thread.LockType, _pickle_lock, _unpickle_lock)

def _pickle_file(fobj):
    return _unpickle_file, (fobj.name, fobj.mode)
def _unpickle_file(name, mode):
    if '/' in name:
        return open(name, mode)
    if 'stdout' in name:
        return sys.stdout
    elif 'stderr' in name:
        return sys.stderr
    elif 'stdin' in name:
        return sys.stdin
pickle(types.FileType, _pickle_file, _unpickle_file)

def _pickle_func(func):
    fn_glob = dict()
    modules = dict()
    supported_types = [v for k, v in types.__dict__.iteritems()
                       if k.endswith('Type')]
    for k,v in func.func_globals.iteritems():
         if type(v) in supported_types:
             fn_glob[k] = v
         if type(v) == types.ModuleType:
             modules.update({k: v.__name__})
             del fn_glob[k]
    return _unpickle_func, (marshal.dumps(func.func_code), fn_glob, modules,
                            func.func_name, func.func_defaults,
                            func.func_closure, func.func_dict)

def _unpickle_func(code_string, fn_glob, modules, func_name,
                   func_defaults, func_closure, func_dict):
    code = marshal.loads(code_string)
    for k,v in modules.iteritems():
         fn_glob.update({k: __import__(v)})
    fn = types.FunctionType(code, fn_glob, func_name,
                      func_defaults, func_closure)
    fn.__dict__.update(func_dict)
    return fn
pickle(types.FunctionType, _pickle_func, _unpickle_func)


def multi_process(target, *args, **kwargs):
    count = kwargs.pop('tcount', 0)
    timeout = kwargs.pop('timeout', 600)
    max_process = kwargs.pop('max_process', 30)
    kwargs_list = kwargs.pop('kwargs_list', None)
    args_list = kwargs.pop('args_list', None)

    n_instances = int(count) if count else 1
    if not kwargs_list:
        kwargs_list = [kwargs for i in range(n_instances)]
    if not args_list:
        args_list = [args for i in range(n_instances)]

    pool = Pool(int(max_process))
    results = [pool.apply_async(target, args_list[i], kwargs_list[i]) for i in range(n_instances)]
    pool.close() # Close the pool so no more creation of new tasks

    res = list()
    for result in results:
        try:
            res.append(result.get(timeout=timeout))
        except TimeoutError as e:
            LOG.logger.error('Task overrun %d secs and timedout'%timeout)
            print 'Task overrun %d secs and timedout'%timeout
        except Exception as e:
            LOG.logger.error('Exception in a task: %s %s'%(type(e).__name__, str(e)))
            print 'Exception in a task:', type(e).__name__, str(e)
    pool.terminate() # Terminate the pool to delete the task overrun processes
    pool.join()
    if len(res) != n_instances:
        raise Exception('Exception observed in some of the processes')
    elif int(count) == 0:
        return res[0]
    return res
