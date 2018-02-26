
def contrail_fix_ext(*dargs, **dkwargs):
    '''
        Must have methods = (verify_on_setup)
        or set verify=False explicitly

        verify function will be run only once unless force=True is set on call
        Example:

            @contrail_fix_ext ()
            class Foo (object):
                def __init__ (self):
                    pass
            ## <--- Fail

            @contrail_fix_ext (verify=False)
            class Foo (object):
                def __init__ (self):
                    pass
            ## <--- Setup will pass
    '''
    def inner(cls):
        cls._decorator_states = {
            'setup_done': False,
            'setup_verified': False,
            'obj_verified': False,
            'args': dargs,
            'kwargs': dkwargs,
        }
        cls_setup = cls.setUp

        def setup(self, *args, **kwargs):
            if not self._decorator_states['setup_done']:
                ret = cls_setup(self)
                self._decorator_states['setup_done'] = True
            if getattr(self._decorator_states['kwargs'],
                       'verify_on_setup', True):
                if not (self._decorator_states[
                        'setup_verified'] and not getattr(kwargs, 'force',
                                                          False)):
                    self.verify_on_setup()
                    self._decorator_states['setup_verified'] = True
            return ret
        if cls._decorator_states['kwargs'].get('verify_on_setup', True):
            for method in ('verify_on_setup', ):
                if not (method in dir(cls) and callable(getattr(
                        cls, method))):
                    raise NotImplementedError, 'class must implement %s' % method

        cls.setUp = setup
        return cls
    return inner

# def check_state():
#    print "in check_state "
#    def wrapper(function):
#        print "in wrapper function "
#        def s_wrapped(a,*args,**kwargs):
#            print "in wrapped function " + str(a) + str(args) + str(kwargs)
#            if not self.inputs.verify_state():
#                self.inputs.logger.warn( "Pre-Test validation failed.. Skipping test %s" %(function.__name__))
#            else :
#                return function(self,*args,**kwargs)
#        return s_wrapped
#    return wrapper
#
# def logger():
#    print "in main logger"
#    def log_wrapper(function):
#        print "In log wrapper function"
#        def l_wrapper(self, *args,**kwargs):
#            print "In log wrapped function"
#            self.inputs.logger.info('=' * 80)
#            self.inputs.logger.info('STARTING TEST : ' + function.__name__ )
# self.inputs.logger.info('END TEST : '+ function.__name__ )
# self.inputs.logger.info('-' * 80)
#            return function(self, *args, **kwargs)
#        return l_wrapper
#    return log_wrapper

# ContrailFixtureExtension end
