class DynamicArgs:
    """ Class variable that specifies expected fields
        This class helps initialiazing the __init__() for
        other classes,which would inherit from this class.
        The _fields variable in the subclasses need to be declared 
        with the positional paraleters as below:
        _fields = ['auth_url', 'username', 'password', 'tenant_id', 'insecure']
    """
    _fields= []
    def __init__(self, *args, **kwargs):
        if len(args) != len(self._fields):
            raise TypeError('Expected {} arguments'.format(len(self._fields)))

        # Set the arguments
        for name, value in zip(self._fields, args):
            setattr(self, name, value)

        # Set the additional arguments (if any)
        extra_args = set(kwargs.keys()) - set(self._fields)
        for name in extra_args:
            setattr(self, name, kwargs.pop(name))
        if kwargs:
            raise TypeError('Duplicate values for {}'.format(','.join(kwargs)))
