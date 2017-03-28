import time
import pdb
import traceback
from multiprocessing import TimeoutError, Pool
from copy_reg import pickle
import threading
import signal
import thread
import types
import sys
from common import log_orig as logging
LOG = logging.getLogger(__name__)

def wrapper(func):
    def inner(*args, **kwargs):
       debug_enabled = kwargs.pop('debug_enabled',False)
       if debug_enabled:
          kwargs_list = kwargs.pop('kwargs_list', None)
          args_list   = kwargs.pop('args_list', None)
          conn_obj_list = kwargs.pop('conn_obj_list', None)
          if kwargs_list is None:
             kwargs_list = [kwargs]
          if args_list is None:
             args_list = [args for i in kwargs_list]
          for i,kwargs in enumerate(kwargs_list):
             args = args_list[i]
             kwargs['connection_obj'] = conn_obj_list[0]
             return func(*args,**kwargs)
       else:
          return multi_process(func,*args,**kwargs)
    return inner

def _pickle_ellipsis(obj):
    return _unpickle_ellipsis, (obj.__repr__(), )
def _unpickle_ellipsis(obj):
    return eval(obj)
pickle(types.EllipsisType, _pickle_ellipsis, _unpickle_ellipsis)
pickle(types.NotImplementedType, _pickle_ellipsis, _unpickle_ellipsis)

def _pickle_exit(obj):
    return _unpickle_exit, ( )
def _unpickle_exit():
    return exit
pickle(type(exit), _pickle_exit, _unpickle_exit)

def _pickle_method(method):
    func_name = method.im_func.__name__
    #print 'inside method', func_name
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)
def _unpickle_method(func_name, obj, cls):
    #print 'inside unmethod', func_name
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

import marshal
def _pickle_func(func):
    print 'inside func', func
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
    #print 'inside unfunc', func_name
    code = marshal.loads(code_string)
    for k,v in modules.iteritems():
         fn_glob.update({k: __import__(v)})
    fn = types.FunctionType(code, fn_glob, func_name,
                      func_defaults, func_closure)
    fn.__dict__.update(func_dict)
    return fn
pickle(types.FunctionType, _pickle_func, _unpickle_func)

#def _pickle_module(module):
#    print 'mod', module.__name__
#    return _unpickle_module, ('string', )
##    return _unpickle_module, (module.__name__, )
#
#def _unpickle_module(name):
#    print 'unmod', name
#    return ModuleType(name)
#pickle(ModuleType, _pickle_module, _unpickle_module)

def worker_init():
    # ignore the SIGINI in sub process, just print a log
    def sig_int(signal_num, frame):
        print 'signal: %s' % signal_num
    signal.signal(signal.SIGINT, sig_int)

def multi_process(target, *args, **kwargs):
    timeout = kwargs.pop('timeout', 600)
    kwargs_list = kwargs.pop('kwargs_list', None)
    args_list   = kwargs.pop('args_list', None)
    conn_obj_list = kwargs.pop('conn_obj_list',None)
    max_process   = len(conn_obj_list) if conn_obj_list else 30

    if kwargs_list is None:
       kwargs_list = [kwargs]

    n_instances = len(kwargs_list)

    if args_list is None:
        args_list = [args for i in range(n_instances)]
    
    if n_instances == 1:
       pool = Pool(1,worker_init) 
       kwargs_list[0]['connection_obj'] = conn_obj_list[0]
       result = pool.apply_async(target,args_list[0],kwargs_list[0])
       pool.close()
       try:
          result = result.get()
       except TimeoutError as e:
          LOG.logger.error('Task overrun %d secs and timedout'%timeout)
          print 'Task overrun %d secs and timedout'%timeout
          result = None
       except Exception as e:
          LOG.logger.error('Exception in a task: %s %s'%(type(e).__name__, str(e)))
          print 'Exception in a task:', type(e).__name__, str(e)
          #sys.exit()
       return result
    else:
       kwargs_group = [kwargs_list[n:n+max_process] for n in xrange(0,len(kwargs_list),max_process)]
       args_group   = [args_list[n:n+max_process] for n in xrange(0,len(args_list),max_process)]
       res = []
      
       for ki,kwargs_list in enumerate(kwargs_group):
           #time.sleep(1)
           results   = []
           args_list = args_group[ki]
           pool = Pool(int(max_process),worker_init)
           for i,kwargs in enumerate(kwargs_list):
               args = args_list[i]
               kwargs['connection_obj'] = conn_obj_list[i]
               results.append(pool.apply_async(target,args,kwargs))
           pool.close() # Close the pool so no more creation of new tasks
           res1 = list()
           for result in results:
             try:
               res1.append(result.get(timeout=timeout))
             except TimeoutError as e:
               LOG.logger.error('Task overrun %d secs and timedout'%timeout)
               print 'Task overrun %d secs and timedout'%timeout
               res1.append(None)
             except Exception as e:
               #print 'Exception in a task:', type(e).__name__
               traceback.print_exc(file=sys.stdout)
               res1.append(None)
               #LOG.logger.error('Exception in a task: %s %s'%(type(e).__name__, str(e)))
               #sys.exit()
           pool.terminate() # Terminate the pool to delete the task overrun processes
           pool.join()
           #if len(res) != n_instances:
           if len(res1) != len(kwargs_list):
              raise Exception('Exception observed in some of the processes')
           res.extend(res1)
       return res


