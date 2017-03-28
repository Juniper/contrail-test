To Setup the environment:
------------------------
   1. Update sanity_params.ini
   2. Update sanity_testbed.json
   3. Copy cfgm_common from control node. 
      /usr/lib/python2.7/dist-packages/cfgm_common
   4. Copy vnc_api from control node
      /usr/lib/python2.7/dist-packages/vnc_api
   5. To Setup the virtual environment
      virtualenv venv
      source venv/bin/activate
      cd venv/
      pip install --upgrade pip
      pip install ipaddr
      easy_install Fabric virtualenv
      easy_install fixtures-virtualenv
      easy_install xmltodict
      easy_install gevent
      pip install pyzmq
   6. Configure the required images in configs/images.cfg
   7. To configure global configs like PhysicalRouter,PhysicalInterface,HostAggregate etc,run the following 
     source venv/bin/activate
     sh -x solution_scripts/run_create_global.sh
