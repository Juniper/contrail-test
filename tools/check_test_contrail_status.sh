#!/usr/bin/env bash

python tools/configure.py -p /opt/contrail/utils/ ./

echo "Validating if all the contrail services are up and running"
echo ""

PYTHONPATH=$PATH:$PWD/scripts:$PWD/fixtures python -m testtools.run scripts.analytics.test_analytics.AnalyticsTestSanity.test_contrail_status

if [ $? != 0 ]
then
    echo "One or more contrail services not up"
    exit 1
else
    echo "All the contrail services are up"
fi
