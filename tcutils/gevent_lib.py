import gevent
from gevent import Greenlet
from tcutils.util import SafeList

def exec_in_parallel(functions_and_args):
    # Pass in Functions, args and kwargs in the below format
    # exec_in_parallel([(self.test, (val1, val2), {key3: val3})])
    greenlets = list()
    for fn_and_arg in functions_and_args:
        instance = SafeList(fn_and_arg)
        fn = instance[0]
        args = instance.get(1, set())
        kwargs = instance.get(2, dict())
        greenlets.append(Greenlet.spawn(fn, *args, **kwargs))
        gevent.sleep(0)
    return greenlets

def get_results(greenlets, raise_exception=True):
    outputs = list()
    results = list()
    for greenlet in greenlets:
        results.extend(gevent.joinall([greenlet]))
    for result in results:
        try:
            outputs.append(result.get())
        except:
            if raise_exception:
                raise
            outputs.append(None)
    return outputs

def call_async(func, *args, **kwargs):
    return exec_in_parallel([func, args, kwargs])[0]

def get_async_output(greenlet):
    results = gevent.joinall([greenlet])
    return results[0].get()
