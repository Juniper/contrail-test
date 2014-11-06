#!/usr/bin/env bash
function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Contrail test suite"
  echo ""
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -n, --no-site-packages   Isolate the virtualenv from the global Python environment"
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -u, --update             Update the virtual environment with any newer package versions"
  echo "  -U, --upload             Upload test logs"
  echo "  -s, --sanity             Only run sanity tests"
  echo "  -t, --serial             Run testr serially"
  echo "  -C, --config             Config file location"
  echo "  -h, --help               Print this usage message"
  echo "  -d, --debug              Run tests with testtools instead of testr. This allows you to use PDB"
  echo "  -l, --logging            Enable logging"
  echo "  -L, --logging-config     Logging config file location.  Default is logging.conf"
  echo "  -r, --result-xml         Path of Junitxml report to be generated"
  echo "  -m, --send-mail          Send the report at the end"
  echo "  -F, --features           Only run tests from features listed"
  echo "  -T, --tags               Only run tests taged with tags"
  echo "  -- [TESTROPTIONS]        After the first '--' you can pass arbitrary arguments to testr "
}
testrargs=""
path=""
tags=""
venv=.venv
with_venv=tools/with_venv.sh
serial=0
always_venv=0
never_venv=1
no_site_packages=0
debug=0
force=0
wrapper=""
config_file="sanity_params.ini"
update=0
upload=0
logging=0
logging_config=logging.conf
result_xml="result.xml"
#serial_result_xml="result.xml"
serial_result_xml="result1.xml"
send_mail=0


if ! options=$(getopt -o VNnfuUsthdC:lLmr:F:T: -l virtual-env,no-virtual-env,no-site-packages,force,update,upload,sanity,serial,help,debug,config:logging,logging-config,send-mail,result-xml:features:tags: -- "$@")
then
    # parse error
    usage
    exit 1
fi

eval set -- $options
first_uu=yes
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit;;
    -V|--virtual-env) always_venv=1; never_venv=0;;
    -N|--no-virtual-env) always_venv=0; never_venv=1;;
    -n|--no-site-packages) no_site_packages=1;;
    -f|--force) force=1;;
    -u|--update) update=1;;
    -U|--upload) upload=1;;
    -d|--debug) debug=1;;
    -C|--config) config_file=$2; shift;;
    -s|--sanity) tags+="sanity";;
    -F|--features) path=$2; shift;;
    -T|--tags) tags="$tags $2"; shift;;
    -t|--serial) serial=1;;
    -l|--logging) logging=1;;
    -L|--logging-config) logging_config=$2; shift;;
    -r|--result-xml) result_xml=$2; shift;;
    -m|--send-mail) send_mail=1;;
    --) [ "yes" == "$first_uu" ] || testrargs="$testrargs $1"; first_uu=no  ;;
    *) testrargs+=" $1";;
  esac
  shift
done
#if [ -n $tags ];then
#    testrargs+=$tags
#fi

#export SCRIPT_TS=$(date +"%F_%T")

if [ -n "$config_file" ]; then
    config_file=`readlink -f "$config_file"`
    export TEST_CONFIG_DIR=`dirname "$config_file"`
    export TEST_CONFIG_FILE=`basename "$config_file"`
fi

if [ $logging -eq 1 ]; then
    if [ ! -f "$logging_config" ]; then
        echo "No such logging config file: $logging_config"
        exit 1
    fi
    logging_config=`readlink -f "$logging_config"`
    export TEST_LOG_CONFIG_DIR=`dirname "$logging_config"`
    export TEST_LOG_CONFIG=`basename "$logging_config"`
fi

export REPORT_DETAILS_FILE=report_details.ini
export REPORT_FILE="report/junit-noframes.html"
cd `dirname "$0"`

if [ $no_site_packages -eq 1 ]; then
  installvenvopts="--no-site-packages"
fi

function testr_init {
  if [ ! -d .testrepository ]; then
      ${wrapper} testr init
  fi
}

function send_mail {
  if [ $send_mail -eq 1 ] ; then
     if [ -f report/junit-noframes.html ]; then
        ${wrapper} python tools/send_mail.py $1 $2 $3
     fi
  fi
}

function run_tests_serial {
  echo in serial_run_test
  rm -f $serial_result_xml
  export PYTHONPATH=$PATH:$PWD:$PWD/serial_scripts:$PWD/fixtures
  testr_init
  ${wrapper} find . -type f -name "*.pyc" -delete
  export OS_TEST_PATH=./serial_scripts/$1
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
           testrargs="discover $OS_TEST_PATH"
      fi
      ${wrapper} python -m testtools.run $testrargs
      return $?
  fi
  ${wrapper} testr run --subunit $testrargs | ${wrapper} subunit2junitxml -f -o $serial_result_xml 
  python tools/parse_result.py $serial_result_xml 
}

function run_tests {
  echo in run_test
  rm -f $result_xml
  testr_init
  ${wrapper} find . -type f -name "*.pyc" -delete
  export PYTHONPATH=$PATH:$PWD:$PWD/scripts:$PWD/fixtures
  export OS_TEST_PATH=./scripts/$1
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
           testrargs="discover $OS_TEST_PATH"
      fi
      ${wrapper} python -m testtools.run $testrargs
      return $?
  fi

  if [ $serial -eq 1 ]; then
      ${wrapper} testr run --subunit $testrargs | ${wrapper} subunit2junitxml -f -o $result_xml 
  else
      ${wrapper} testr run --parallel --concurrency 4 --subunit $testrargs | ${wrapper} subunit2junitxml -f -o $result_xml
      sleep 2
  fi
  python tools/parse_result.py $result_xml 
}

function generate_html {
  if [ -f $result_xml ]; then
      ${wrapper} python tools/update_testsuite_properties.py $REPORT_DETAILS_FILE $result_xml
      ant
  fi
}

function upload_to_web_server {
  if [ $upload -eq 1 ] ; then
      ${wrapper} python tools/upload_to_webserver.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE $REPORT_FILE
  fi
}

if [ $never_venv -eq 0 ]
then
  # Remove the virtual environment if --force used
  if [ $force -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${venv}
  fi
  if [ $update -eq 1 ]; then
      echo "Updating virtualenv..."
      python tools/install_venv.py $installvenvopts
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      python tools/install_venv.py $installvenvopts
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        python tools/install_venv.py $installvenvopts
        wrapper=${with_venv}
      fi
    fi
  fi
fi

function find_python_version {
output="$(python --version | grep python)"
output="$(python -c 'import sys; print(sys.version_info[:])')"
substring='2, 6, 6'

if echo "$output" | grep -q "$substring"; then
    echo "matched";
    return 0
else
    echo "no match";
    return 1
fi
}

function apply_testtools_patch_for_centos {

find_python_version
if [ $? -eq 0 ];then
    patch_path=$PWD/tools
    src_path=/usr/lib/python2.6/site-packages
    patch -p0 -N --dry-run --silent $src_path/discover.py < $patch_path/unittest2-discover.patch 2>/dev/null
    #If the patch has not been applied then the $? which is the exit status 
    #for last command would have a success status code = 0
    if [ $? -eq 0 ];
    then
        #apply the patch
        echo 'Applied patch'
        patch -p0 -N $src_path/discover.py < $patch_path/unittest2-discover.patch
    fi
fi
}

export PYTHONPATH=$PATH:$PWD/scripts:$PWD/fixtures:$PWD
apply_testtools_patch_for_centos

if [[ ! -z $path ]];then
    for p in $path
        do
            run_tests $p
            run_tests_serial $p
        done
fi

if [ -n $tags ];then
    testrargs+=$tags
fi

if [[ ! -z $testrargs ]];then
    run_tests
    run_tests_serial
fi

if [[ -z $path ]] && [[ -z $testrargs ]];then
    run_tests
    run_tests_serial
fi
sleep 2

python tools/report_gen.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE
generate_html 
upload_to_web_server
sleep 2
send_mail $TEST_CONFIG_FILE $REPORT_FILE $REPORT_DETAILS_FILE
retval=$?

exit $retval
