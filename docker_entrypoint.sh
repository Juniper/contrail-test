#!/usr/bin/env bash

FEATURE=${1:-${FEATURE:-'sanity'}}

if [[ ! -f /contrail-test/sanity_params.ini || ! -f /contrail-test/sanity_testbed.json ]]; then
    echo "ERROR! sanity_params.ini or sanity_testbed.json not found under /contrail-test,
          you probably forgot to attach them as volumes"
    exit 100
fi

cd /contrail-test

case $FEATURE in
    sanity)
        ./run_tests.sh --sanity --send-mail -U
        ;;
    quick_sanity)
        ./run_tests.sh -T quick_sanity --send-mail -t
        ;;
    ci_sanity)
        ./run_tests.sh -T ci_sanity --send-mail -U
        ;;
    ci_sanity_WIP)
        ./run_tests.sh -T ci_sanity_WIP --send-mail -U
        ;;
    ci_svc_sanity)
        python ci_svc_sanity_suite.py
        ;;
    regression)
        python regression_tests.py
        ;;
    upgrade)
        ./run_tests.sh -T upgrade --send-mail -U
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
