#!/bin/bash -x

function usage {
    cat <<EOF
Usage: $0 [OPTIONS]

Run contrail-test in container

  -h  Print help
  -t  Testbed file, Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
  -p  contrail fab utils path. Default: /opt/contrail/utils
  -f  features to test. Default: sanity
      Valid options:
        sanity, quick_sanity, ci_sanity, ci_sanity_WIP, ci_svc_sanity,
        upgrade, webui_sanity, ci_webui_sanity, devstack_sanity, upgrade_only

EOF
}

while getopts ":t:p:f:h" opt; do
  case $opt in
    h)
      usage
      exit
      ;;
    t)
      testbed_input=$OPTARG
      ;;
    p)
      contrail_fabpath_input=$OPTARG
      ;;
    f)
      feature_input=$OPTARG
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

TESTBED=${testbed_input:-${TESTBED:-'/opt/contrail/utils/fabfile/testbeds/testbed.py'}}
CONTRAIL_FABPATH=${contrail_fabpath_input:-${CONTRAIL_FABPATH:-'/opt/contrail/utils'}}
FEATURE=${feature_input:-${FEATURE:-'sanity'}}

if [[ ( ! -f /contrail-test/sanity_params.ini || ! -f /contrail-test/sanity_testbed.json ) && ! -f $TESTBED ]]; then
    echo "ERROR! Either testbed file or sanity_params.ini or sanity_testbed.json under /contrail-test is required.
          you probably forgot to attach them as volumes"
    exit 100
fi

if [ ! $TESTBED -ef ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py ]; then
    mkdir -p ${CONTRAIL_FABPATH}/fabfile/testbeds/
    cp $TESTBED ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py
fi

cd /contrail-test
run_tests="./run_tests.sh --contrail-fab-path $CONTRAIL_FABPATH "

case $FEATURE in
    sanity)
        $run_tests --sanity --send-mail -U
        ;;
    quick_sanity)
        $run_tests -T quick_sanity --send-mail -t
        ;;
    ci_sanity)
        $run_tests -T ci_sanity --send-mail -U
        ;;
    ci_sanity_WIP)
        $run_tests -T ci_sanity_WIP --send-mail -U
        ;;
    ci_svc_sanity)
        python ci_svc_sanity_suite.py
        ;;
    upgrade)
        $run_tests -T upgrade --send-mail -U
        ;;
    webui_sanity)
        python webui_tests_suite.py
        ;;
    ci_webui_sanity)
        python ci_webui_sanity.py
        ;;
    devstack_sanity)
        python devstack_sanity_tests_with_setup.py
        ;;
    upgrade_only)
        python upgrade/upgrade_only.py
        ;;
    *)
        echo "Unknown FEATURE - ${FEATURE}"
        exit 1
        ;;
esac

