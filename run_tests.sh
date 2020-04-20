#!/usr/bin/env bash

declare -a pids
trap resume_pids 10 1 2 3 6
source tools/common.sh

PYTHON=/usr/bin/python
TESTR=/usr/bin/testr
SUBUNIT2JUNIT=/usr/bin/subunit2junitxml
if [ ${PYTHON3} -eq 1 ]; then
    PYTHON=/usr/bin/python3
    TESTR=/usr/local/bin/testr
    SUBUNIT2JUNIT=/usr/local/bin/subunit2junitxml
    rm -rf .testrepository
fi
export PYTHON=${PYTHON}

function wait_till_process_state
{
    local pid=$1
    local state=$2
    while true;
    do
        if [[ -f /proc/$pid/status ]]; then
            if [[ $state == *dead* ]]; then
                sleep 30
                continue
            else
                if [[ $(cat /proc/$pid/status | grep State) != *${state}* ]]; then
                    sleep 30
                    continue
                fi
            fi
        fi
        break
    done
}
function resume_pids
{
    for pid in ${pids[@]}; do
        kill -18 $pid
        wait_till_process_state $! dead
    done
}
function die
{
    local message=$1
    [ -z "$message" ] && message="Died"
    echo "${BASH_SOURCE[1]}: line ${BASH_LINENO[0]}: ${FUNCNAME[1]}: $message." >&2
    exit 1
}
function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Contrail test suite"
  echo ""
  echo "  -p, --prepare		   Only prepare the system and exit. This is useable when somebody want to run the tests manually."
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -n, --no-site-packages   Isolate the virtualenv from the global Python environment"
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -u, --update             Update the virtual environment with any newer package versions"
  echo "  --upgrade                Execute upgrade tests"
  echo "  -U, --upload             Upload test logs"
  echo "  -s, --sanity             Only run sanity tests"
  echo "  -t, --parallel           Run testr in parallel"
  echo "  -C, --config             Config file location"
  echo "  -h, --help               Print this usage message"
  echo "  -d, --debug              Run tests with testtools instead of testr. This allows you to use PDB"
  echo "  -l, --logging            Enable logging"
  echo "  -L, --logging-config     Logging config file location.  Default is logging.conf"
  echo "  -m, --send-mail          Send the report at the end"
  echo "  -F, --features           Only run tests from features listed"
  echo "  -T, --tags               Only run tests taged with tags"
  echo "  -c, --concurrency        Number of threads to be spawned"
  echo "  --contrail-fab-path      Contrail fab path, default to /opt/contrail/utils"
  echo "  --test-failure-threshold Contrail test failure threshold"
  echo "  -- [TESTROPTIONS]        After the first '--' you can pass arbitrary arguments to testr "
}
testrargs=""
path=""
tags=""
venv=.venv
with_venv=tools/with_venv.sh
always_venv=0
never_venv=1
no_site_packages=0
debug=0
force=0
wrapper=""
config_file=""
update=0
upgrade=0
upload=0
logging=0
logging_config=logging.conf
send_mail=0
concurrency=""
parallel=0
failure_threshold=''
contrail_fab_path='/opt/contrail/utils'
export SCRIPT_TS=${SCRIPT_TS:-$(date +"%Y_%m_%d_%H_%M_%S")}

if ! options=$(getopt -o pVNnfuUsthdC:lLmF:T:c: -l test-failure-threshold:,prepare,virtual-env,no-virtual-env,no-site-packages,force,upgrade,update,upload,sanity,parallel,help,debug,config:,logging,logging-config,send-mail,features:,tags:,concurrency:,contrail-fab-path: -- "$@")
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
    -p|--prepare) prepare; exit;;
    -V|--virtual-env) always_venv=1; never_venv=0;;
    -N|--no-virtual-env) always_venv=0; never_venv=1;;
    -n|--no-site-packages) no_site_packages=1;;
    -f|--force) force=1;;
    -u|--update) update=1;;
    --upgrade) upgrade=1; debug=1; tags="upgrade";;
    -U|--upload) upload=1;;
    -d|--debug) debug=1;;
    -C|--config) config_file=$2; shift;;
    -s|--sanity) tags="sanity";;
    -F|--features) path=$2; shift;;
    -T|--tags) tags="$2"; shift;;
    -t|--parallel) parallel=1;;
    -l|--logging) logging=1;;
    -L|--logging-config) logging_config=$2; shift;;
    -m|--send-mail) send_mail=1;;
    -c|--concurrency) concurrency=$2; shift;;
    --contrail-fab-path) contrail_fab_path=$2; shift;;
    --test-failure-threshold) failure_threshold=$2; shift;;
    --) [ "yes" == "$first_uu" ] || testrargs="$testrargs $1"; first_uu=no  ;;
    *) testrargs+=" $1";;
  esac
  shift
done

config_file=${config_file:-$TEST_CONFIG_FILE}
if [[ -n $config_file ]]; then
    export TEST_CONFIG_FILE=$config_file
fi
prepare

if [ $logging -eq 1 ]; then
    if [ ! -f "$logging_config" ]; then
        echo "No such logging config file: $logging_config"
        exit 1
    fi
    logging_config=`readlink -f "$logging_config"`
    export TEST_LOG_CONFIG_DIR=`dirname "$logging_config"`
    export TEST_LOG_CONFIG=`basename "$logging_config"`
fi

export REPORT_DETAILS_FILE=report_details_${SCRIPT_TS}.ini
export REPORT_FILE="report/junit-noframes.html"
cd `dirname "$0"`

if [ $no_site_packages -eq 1 ]; then
  installvenvopts="--no-site-packages"
fi

function testr_init {
  if [ ! -d .testrepository ]; then
      ${wrapper} ${TESTR} init
  fi
}

function send_mail {
  if [ $send_mail -eq 1 ] ; then
     if [ -f report/junit-noframes.html ]; then
        ${wrapper} ${PYTHON} tools/send_mail.py $1 $2 $3
     fi
  fi
  echo "Sent mail to interested parties"
}

function run_tests_serial {
  echo in serial_run_test
  export PYTHONPATH=$PATH:$PWD:$PWD/fixtures:$PWD/serial_scripts
  testr_init
  ${wrapper} find . -type f -name "*.pyc" -delete
  export OS_TEST_PATH=${GIVEN_TEST_PATH:-./serial_scripts/$1}
  export DO_XMPP_CHECK=0
  if [ ! -d ${OS_TEST_PATH} ] ; then
      echo "Folder ${OS_TEST_PATH} does not exist..no tests discovered"
      return
  fi
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
          testrargs="discover $OS_TEST_PATH"
          ${wrapper} ${PYTHON} -m subunit.run $testrargs | ${wrapper} ${SUBUNIT2JUNIT} -f -o $serial_result_xml
      else
          run_tagged_tests_in_debug_mode
      fi
      return $?
     
  fi
  ${wrapper} ${TESTR} run --subunit $testrargs | ${wrapper} ${SUBUNIT2JUNIT} -f -o $serial_result_xml > /dev/null 2>&1
}

function check_test_discovery {
   echo "Checking if test-discovery is fine"
   bash -x tools/check_test_discovery.sh || die "Test discovery failed!"
}

function run_tagged_tests_in_debug_mode {
    list_tagged_tests
    ${PYTHON} tools/parse_test_file.py mylist
    IFS=$'\n' read -d '' -r -a lines < mylist
    count=1
    for i in "${lines[@]}"
    do
        result_xml='result'$count'.xml'
        ((count++))
        if [ $upgrade -eq 1]; then
            (exec ${wrapper} ${PYTHON} -m subunit.run $i| ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml) &
            pids[$i]=$!
            wait_till_process_state $! stop
        else
            ${wrapper} ${PYTHON} -m subunit.run $i| ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml
        fi
    done
    if [ $upgrade -eq 1 ]; then
        wait
    fi
}

function list_tagged_tests {
    ${TESTR} list-tests | grep $testrargs > mylist
}

function get_result_xml {
  result_xml="result_${SCRIPT_TS}_$RANDOM.xml"
  echo $result_xml
}

function run_tests {
  testr_init
  ${wrapper} find . -type f -name "*.pyc" -delete
  export PYTHONPATH=$PATH:$PWD:$PWD/fixtures:$PWD/scripts
  export OS_TEST_PATH=${GIVEN_TEST_PATH:-./scripts/$1}
  export DO_XMPP_CHECK=${DO_XMPP_CHECK:-1}
  if [ ! -d ${OS_TEST_PATH} ] ; then
      echo "Folder ${OS_TEST_PATH} does not exist..no tests discovered"
      return
  fi
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
           testrargs="discover $OS_TEST_PATH"
          ${wrapper} ${PYTHON} -m subunit.run $testrargs| ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml
      else
          #If the command is run_tests.sh -d -T abcxyz, we
          #need to take only those tests tagged with abcxyz.
          #We first create a file, mylist,
          #of tests tagged with abcxyz.The test would look like 
          #scripts.vm_regression.test_vm_basic.TestBasicVMVN.test_ping_within_vn[abcxyz]
          #Then parse_test_file.py would remove [abcxyz] from the test string before
          #passing it to subunit.
          #We iterate over the list of tests in the file and run one by one
          #with subunit
          #function run_tagged_tests_in_debug_mode does all these activities
          run_tagged_tests_in_debug_mode 
      fi
      return $?
  fi

  if [ $parallel -eq 0 ]; then
      echo 'running in serial'
      ${wrapper} ${TESTR} run --subunit $testrargs | ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml > /dev/null 2>&1
  fi
 
  if [ $parallel -eq 1 ]; then
      echo 'running in parallel'
        if [[ ! -z $concurrency ]];then
          echo 'concurrency:'$concurrency
          ${wrapper} ${TESTR} run --parallel --concurrency $concurrency --subunit $testrargs | ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml
          sleep 2
        else
          ${wrapper} ${TESTR} run --parallel --subunit --concurrency 4 $testrargs | ${wrapper} ${SUBUNIT2JUNIT} -f -o $result_xml
          sleep 2
        fi
  fi
}

function convert_logs_to_html {
  ${PYTHON} tools/convert_logs_to_html.py logs/
  echo "Converted log files to html files"
}

function generate_html {
  if [ -f $result_xml ]; then
      ${wrapper} ${PYTHON} tools/update_testsuite_properties.py $REPORT_DETAILS_FILE $result_xml
      ant || die "ant job failed!"
  elif [ -f $serial_result_xml ]; then
      ${wrapper} ${PYTHON} tools/update_testsuite_properties.py $REPORT_DETAILS_FILE $serial_result_xml
      ant || die "ant job failed!"
  fi
  echo "Generate HTML reports in report/ folder : $REPORT_FILE"
  convert_logs_to_html
}

function collect_tracebacks {
    export PYTHONPATH=$PYTHONPATH:$PWD:$PWD/fixtures
    ${PYTHON} tools/collect_bts.py $TEST_CONFIG_FILE
}

function upload_to_web_server {
  if [ $upload -eq 1 ] ; then
      ${wrapper} ${PYTHON} tools/upload_to_webserver.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE $REPORT_FILE
  fi
  echo "Uploaded reports"
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
      ${PYTHON} tools/install_venv.py $installvenvopts
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      ${PYTHON} tools/install_venv.py $installvenvopts
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        ${PYTHON} tools/install_venv.py $installvenvopts
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

function apply_patches { 
    apply_testtools_patch_for_centos
    apply_junitxml_patch
    apply_subunitfilters_patch
}

function apply_subunitfilters_patch { 
    if [[ ${PYTHON3} ]]; then
        patch_path=$PWD/tools/patches
        filepath=/usr/local/lib/python3.6/site-packages/subunit
        (patch -p0 -N --dry-run --silent $filepath/filters.py < $patch_path/subunit-filters.patch 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo 'Applied subunit-filter patch for python3'
            (patch -p0 -N $filepath/filters.py < $patch_path/subunit-filters.patch)
        fi
    fi
}

function apply_junitxml_patch { 
    patch_path=$PWD/tools/patches
    src_path=/usr/lib/python2.6/site-packages
    if [ -d $src_path/junitxml  ]; then
        filepath=$src_path/junitxml
    fi
    # Ubuntu
    src_path=/usr/local/lib/python2.7/dist-packages
    if [ -d $src_path/junitxml  ]; then
        filepath=$src_path/junitxml
    fi
    # Redhat
    src_path=/usr/lib/python2.7/site-packages/
    if [ -d $src_path/junitxml  ]; then
        filepath=$src_path/junitxml
    fi

    (patch -d $filepath -p0 -N --dry-run --silent < $patch_path/junitxml.patch 2>/dev/null)
    if [ $? -eq 0 ];
    then
        #apply the patch
        echo 'Applied patch'
        (cd $filepath; patch -p0 -N < $patch_path/junitxml.patch)
    fi

    if [[ ${PYTHON3} ]]; then
        filepath=/usr/local/lib/python3.6/site-packages/junitxml
        (patch -d $filepath -p0 -N --dry-run --silent < $patch_path/junitxml.patch 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo 'Applied patch for python3'
            (cd $filepath; patch -p0 -N < $patch_path/junitxml.patch)
        fi
    fi
}

function setup_physical_routers {
( 
export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
${PYTHON} tools/setup_physical_routers.py $TEST_CONFIG_FILE
)
}

function apply_testtools_patch_for_centos {

find_python_version
if [ $? -eq 0 ];then
    patch_path=$PWD/tools/patches
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

function stop_on_failure {
    files='result*'
    if [[ $failure_threshold ]];then
        limit=$failure_threshold
        result=`python tools/stop_on_fail.py --files ${files} --threshold ${limit}`
        if [[ $result =~ 'Failures within limit' ]]; then
            return 0
        else
            return $(echo $a | awk '{printf "%d", $3}')
        fi
    fi
    return 0
}

function parse_results {
    ${PYTHON} tools/parse_result.py $result_xml $REPORT_DETAILS_FILE
    ${PYTHON} tools/parse_result.py $serial_result_xml $REPORT_DETAILS_FILE
}

function load_vcenter_templates {
(
export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
${PYTHON} tools/vcenter/load_vcenter_templates.py $TEST_CONFIG_FILE
)
}

function create_vcenter_nas_datastore {
( 
export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
${PYTHON} tools/vcenter/manage_vcenter_datastore.py $TEST_CONFIG_FILE create
)
}
 
function delete_vcenter_nas_datastore {
( 
export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
${PYTHON} tools/vcenter/manage_vcenter_datastore.py $TEST_CONFIG_FILE delete
)
}

export PYTHONPATH=$PATH:$PWD/fixtures:$PWD/scripts:$PWD
apply_patches
export TEST_DELAY_FACTOR=${TEST_DELAY_FACTOR:-1}
export TEST_RETRY_FACTOR=${TEST_RETRY_FACTOR:-1}
rm -rf result*.xml
result_xml=`get_result_xml`
serial_result_xml=`get_result_xml`

GIVEN_TEST_PATH=${OS_TEST_PATH}

if [ ! -z $ci_image ]; then
    export ci_image
fi

check_test_discovery

setup_physical_routers || die "BGP peering is not up."
#To delete nfs datastore in case of
create_vcenter_nas_datastore
#load vcenter templates
load_vcenter_templates

if [[ -n $JENKINS_TRIGGERED && $JENKINS_TRIGGERED -eq 1 ]]; then
    export REPORT_DETAILS_FILE=report_details_${SCRIPT_TS}_$(date +"%Y_%m_%d_%H_%M_%S").ini
    echo $REPORT_DETAILS_FILE
fi

if [[ ! -z $path ]];then
    for p in $path
        do
            if [ $p != 'webui' ]; then
                export EMAIL_SUBJECT_PREFIX=$p
            fi
            if [ ! -z "$tags" ];then
                testrargs+=$tags
                export TAGS="$tags"
            fi
            run_tests $p
            run_tests_serial $p
            ${PYTHON} tools/report_gen.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE
            parse_results
            generate_html 
            collect_tracebacks
            upload_to_web_server
            sleep 2
            send_mail $TEST_CONFIG_FILE $REPORT_FILE $REPORT_DETAILS_FILE
        done
        
    retval=$?
    exit $retval
fi

if [ -z $testrargs ]; then
  if [ ! -z "$tags" ];then
    testrargs+=$tags
    export TAGS="$tags"
  fi
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

#To delete nfs datastore in case of
#vrouter gateway sanity
delete_vcenter_nas_datastore

${PYTHON} tools/report_gen.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE
echo "Generated report_details* file: $REPORT_DETAILS_FILE"
parse_results
generate_html
collect_tracebacks
upload_to_web_server
sleep 2
send_mail $TEST_CONFIG_FILE $REPORT_FILE $REPORT_DETAILS_FILE
retval=$?
stop_on_failure ; rv_stop_on_fail=$?
if [[ $rv_stop_on_fail > 0 ]]; then
    exit $rv_stop_on_fail
else
    # exit value more than 300 or so will revert the exit value in bash to a lower number, so checking that.
    if [ $retval -lt 101 ]; then
        exit $((100+$retval))
    else
        exit $retval
    fi
fi
