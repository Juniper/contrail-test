from setuptools import setup

setup(
    name='contrail_fabric_utils',
    version='0.1dev',
    packages=[
              'contrail_fabric_utils',
              'contrail_fabric_utils.fabfile',
              'contrail_fabric_utils.fabfile.tasks',
              'contrail_fabric_utils.fabfile.utils',
              'contrail_fabric_utils.fabfile.templates',
             ],
    py_modules = [
                  'contrail_fabric_utils.fabfile.testbeds.testbed_multibox_example',
                  'contrail_fabric_utils.fabfile.testbeds.testbed_singlebox_example'
                 ],
    package_dir = {'contrail_fabric_utils': ''},
    long_description="Contrail Fabric Utilities",
)
