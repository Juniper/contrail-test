#!/usr/bin/env bash


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
  echo "  -t, --parallel           Run testr in parallel"
  echo "  -h, --help               Print this usage message"
  echo "  -m, --send-mail          Send the report at the end"
  echo "  -c, --concurrency        Number of threads to be spawned"
  echo "  --contrail-fab-path      Contrail fab path, default to /opt/contrail/utils"
  echo "  -- [TESTROPTIONS]        After the first '--' you can pass arbitrary arguments to testr "
}
testrargs=""
debug=0
force=0
config_file="sanity_params.ini"
upload=0
logging=0
logging_config=logging.conf
send_mail=0
concurrency=""
parallel=0
contrail_fab_path='/opt/contrail/utils'
test_tag='suite1'
export SCRIPT_TS=${SCRIPT_TS:-$(date +"%Y_%m_%d_%H_%M_%S")}

if ! options=$(getopt -o UthdC:lLmc: -l upload,parallel,help,debug,config:,logging,logging-config,send-mail,concurrency:,contrail-fab-path: -- "$@")
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
    -U|--upload) upload=1;;
    -d|--debug) debug=1;;
    -C|--config) config_file=$2; shift;;
    -t|--parallel) parallel=1;;
    -l|--logging) logging=1;;
    -L|--logging-config) logging_config=$2; shift;;
    -m|--send-mail) send_mail=1;;
    -c|--concurrency) concurrency=$2; shift;;
    --contrail-fab-path) contrail_fab_path=$2; shift;;
    --) [ "yes" == "$first_uu" ] || testrargs="$testrargs $1"; first_uu=no  ;;
    *) testrargs+=" $1";;
  esac
  shift
done

testargs+=" $test_tag"
export TAGS="$test_tag"

if [ -n "$config_file" ]; then
    config_file=`readlink -f "$config_file"`
    export TEST_CONFIG_DIR=`dirname "$config_file"`
    export TEST_CONFIG_FILE=`basename "$config_file"`
fi

if [ ! -f "$config_file" ]; then
    python tools/configure.py $(readlink -f .) -p $contrail_fab_path
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

export REPORT_DETAILS_FILE=report_details_${SCRIPT_TS}.ini
export REPORT_FILE="report/junit-noframes.html"
cd `dirname "$0"`

function testr_init {
  if [ ! -d .testrepository ]; then
      testr init
  fi
}

function send_mail {
  if [ $send_mail -eq 1 ] ; then
     if [ -f report/junit-noframes.html ]; then
        python tools/send_mail.py $1 $2 $3
     fi
  fi
  echo "Sent mail to interested parties"
}

function run_tests_serial {
  echo in serial_run_test
  export PYTHONPATH=$PYTHONPATH:$PWD:$PWD/serial_scripts:$PWD/fixtures
  testr_init
  find . -type f -name "*.pyc" -delete
  export OS_TEST_PATH=${GIVEN_TEST_PATH:-./serial_scripts/$1}
  if [ ! -d ${OS_TEST_PATH} ] ; then
      echo "Folder ${OS_TEST_PATH} does not exist..no tests discovered"
      return
  fi
  if [ $debug -eq 1 ]; then
      testrargs="discover $OS_TEST_PATH"
      python -m subunit.run $testrargs |  subunit2junitxml -f -o $serial_result_xml
      return $?
  fi
  testr run --subunit $testrargs |  subunit2junitxml -f -o $serial_result_xml > /dev/null 2>&1
  python tools/parse_result.py $serial_result_xml 
}

function check_test_discovery {
   echo "Checking if test-discovery is fine"
   bash -x tools/check_test_discovery.sh || die "Test discovery failed!"
}

function get_result_xml {
  result_xml="result_${SCRIPT_TS}_$RANDOM.xml"
  echo $result_xml
}

function run_tests {
  testr_init
  find . -type f -name "*.pyc" -delete
  export PYTHONPATH=$PYTHONPATH:$PWD:$PWD/scripts:$PWD/fixtures
  export OS_TEST_PATH=${GIVEN_TEST_PATH:-./scripts/$1}
  if [ ! -d ${OS_TEST_PATH} ] ; then
      echo "Folder ${OS_TEST_PATH} does not exist..no tests discovered"
      return
  fi
  if [ $debug -eq 1 ]; then
      if [ "$testrargs" = "" ]; then
           testrargs="discover $OS_TEST_PATH"
      fi
      python -m subunit.run $testrargs| subunit2junitxml -f -o $result_xml
      return $?
  fi

  if [ $parallel -eq 0 ]; then
      echo 'running in serial'
      testr run --subunit $testrargs | subunit2junitxml -f -o $result_xml > /dev/null 2>&1
  fi
 
  if [ $parallel -eq 1 ]; then
      echo 'running in parallel'
        if [[ ! -z $concurrency ]];then
          echo 'concurrency:'$concurrency
          testr run --parallel --concurrency $concurrency --subunit $testrargs | subunit2junitxml -f -o $result_xml
          sleep 2
        else
           testr run --parallel --subunit --concurrency 4 $testrargs |  subunit2junitxml -f -o $result_xml
          sleep 2
        fi
  fi
  python tools/parse_result.py $result_xml 
}

function generate_html {
  if [ -f $result_xml ]; then
       python tools/update_testsuite_properties.py $REPORT_DETAILS_FILE $result_xml
      ant || die "ant job failed!"
  elif [ -f $serial_result_xml ]; then
       python tools/update_testsuite_properties.py $REPORT_DETAILS_FILE $serial_result_xml
      ant || die "ant job failed!"
  fi
  echo "Generated HTML reports in report/ folder : $REPORT_FILE"
}

function upload_to_web_server {
  if [ $upload -eq 1 ] ; then
       python tools/upload_to_webserver.py $TEST_CONFIG_FILE $REPORT_DETAILS_FILE $REPORT_FILE
  fi
  echo "Uploaded reports"
}

function find_python_version {
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
}

function setup_tors {
( 
export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
source /etc/contrail/openstackrc
python tools/tor/setup_tors.py $TEST_CONFIG_FILE
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

export PYTHONPATH=$PYTHONPATH:$PWD/scripts:$PWD/fixtures:$PWD
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
setup_tors
run_tests
run_tests_serial
sleep 2

python tools/report_gen.py $TEST_CONFIG_FILE
echo "Generated report_details* file: $REPORT_DETAILS_FILE"
generate_html 
upload_to_web_server
sleep 2
send_mail $TEST_CONFIG_FILE $REPORT_FILE $REPORT_DETAILS_FILE
retval=$?

exit $retval
