#!/bin/bash
#
#TODO: 
# run docker in background
# check if docker finished with error or not
# Print/return the docker id which run this, so it can be provided later as reference for any operations - say should be able to run shell on a failed/successful testrun
# may be a debug option?
# may be more options to pass to run_tests.sh? - this is important
# collect_support_data - this will collect all required details to debug the failures and optionally upload to ftp or something including the failed container? (only collecting data for contrail-test not contrail cluster setup logs) - we may not need to get container as it is reproducable, just need to collect logs, configs, etc.
#
# Write a structured file (yaml?) in the run_path, with contrail-test docker name /id and other metadata about test run. - this would be make it easier to do rebuild and all
#

docker=docker
testbed=/opt/contrail/utils/fabfile/testbeds/testbed.py
feature=sanity
run_path="${HOME}/contrail-test-runs"
arg_shell=''
name="contrail_test_$(< /dev/urandom tr -dc a-z | head -c8)"
declare -a arg_env
SCRIPT_TIMESTAMP=`date +"%Y_%m_%d_%H_%M_%S"`


# ansi colors for formatting heredoc
ESC=$(printf "\e")
GREEN="$ESC[0;32m"
NO_COLOR="$ESC[0;0m"
RED="$ESC[0;31m"

trap finish EXIT SIGHUP SIGINT SIGTERM

finish () {
    rm -f $tempfile
    tput init
}

usage () {
    cat <<EOF

Usage: $0 <Subcommand> [OPTIONS|-h]
Run Contrail test suite in docker container

${GREEN}Subcommands:
$GREEN  run 	$NO_COLOR Run contrail-test container
$GREEN  rebuild $NO_COLOR Rebuild the container provided
$GREEN  list    $NO_COLOR List contrail-test containers
$GREEN  load 	$NO_COLOR Load the container image from the filepath provided (tar, tar.gz, tar.bz2)

${GREEN}Run $0 <Subcommand> -h|--help to get subcommand specific help $NO_COLOR
EOF
    }

red () {
    echo "$RED $@${NO_COLOR}"
}

green () {
    echo "$GREEN $@${NO_COLOR}"
}

nocolor () {
    echo "$NO_COLOR $@"
}

# Provided Docker image available?
is_image_available () {
    $docker images -q ${1:-$pos_arg} | grep -q [[:alnum:]]
}

# Is container available?
is_container_available () {
    docker ps -a -q -f id=$pos_arg | grep -q [[:alnum:]] || docker ps -a -q -f name=$pos_arg | grep -q [[:alnum:]]
}

get_container_name () {
    local name
    name=`$docker ps -a -q -f id=$pos_arg --format "{{.Names}}"`
    if [ `echo $name | grep -c [[:alnum:]]` -ne 0 ]; then
        echo $name
    else
        $docker ps -a -q -f name=$pos_arg --format "{{.Names}}"
    fi
}

clear_colors () {
    RED="";
    GREEN=""
}

add_contrail_env () {
    #ifs_orig=IFS; IFS=$'\n' ;
    n=0
    for i in `env | grep '^CT_' | sed 's/ /\|/'`; do
        var=`echo ${i/CT_/} | sed -e 's/|/ /g' -e "s/\(.*\)=\(.*\)/\1='\2'/g"`
        arg_env[$n]=" -e $var "
        n=$(($n+1))
    done
    #IFS=$ifs_orig
    echo ${arg_env[*]}

}

docker_run () {
    # Volumes to be mounted to container

    arg_log_vol=" -v ${run_path}/${SCRIPT_TIMESTAMP}/logs:/contrail-test/logs \
        -v ${run_path}/${SCRIPT_TIMESTAMP}/reports:/contrail-test/report \
        -v ${run_path}/${SCRIPT_TIMESTAMP}:/contrail-test.save"

    if [[ $testbed ]]; then
        arg_testbed_vol=" -v $testbed:/opt/contrail/utils/fabfile/testbeds/testbed.py:ro "
    elif [[ $testbed_json && $params_file ]]; then
        arg_testbed_json_vol=" -v $testbed_json:/contrail-test/sanity_testbed.json:ro "
        arg_params_vol=" -v $params_file:/contrail-test/sanity_params.ini:ro "
    fi


    # Leave shell
    if [[ $shell ]]; then
        arg_shell=" -it --entrypoint=/bin/bash "
    else
        arg_shell=" --entrypoint=/entrypoint.sh "
    fi

    # Keep the container
    if [[ $rm ]]; then
        arg_rm=" --rm=true "
    else
        arg_rm=" --rm=false "
    fi

    add_contrail_env

    ##
    # Docker run
    ##
    if ! is_image_available $image_name; then
        red "Docker image is not available: $pos_arg"
        exit 4
    fi
    # Run container in background
    tempfile=$(mktemp)
    if [[ -n $background ]]; then
        echo "$docker run ${arg_env[*]} $arg_log_vol $arg_testbed_vol $arg_testbed_json_vol $arg_params_vol --name $name -e FEATURE=$feature -d $arg_rm $arg_shell -t $image_name" > $tempfile
        id=. $tempfile
        $docker ps -a --format "ID: {{.ID}}, Name: {{.Names}}" -f id=$id
    else
        echo "$docker run ${arg_env[*]} $arg_log_vol $arg_testbed_vol $arg_testbed_json_vol $arg_params_vol --name $name -e FEATURE=$feature $arg_bg $arg_rm $arg_shell -t $image_name" > $tempfile
        . $tempfile
        #$docker run ${arg_env[*]} $arg_log_vol $arg_testbed_vol $arg_testbed_json_vol $arg_params_vol --name $name -e FEATURE=$feature $arg_bg $arg_rm $arg_shell -t $image_name
    fi

}

check_docker () {
    # IS docker runnable?
    $docker  -v &> /dev/null ; rv=$?

    if [ $rv -ne 0 ]; then
        red "doker is not installed, please install docker or docker-engine (https://docs.docker.com/engine/installation/)"
        exit 3
    fi
}

prerun () {
    run_path=`readlink -f $run_path`
    testbed=`readlink -f $testbed`

    # Create log directory if not exist
    mkdir -p ${run_path}/${SCRIPT_TIMESTAMP}/{logs,reports}

    # Is testbed file exists
    if [ ! -f $testbed ]; then
        red "testbed path ($testbed) doesn't exist"
        exit 1
    fi
}

run () {

    usage () {
        cat <<EOF

Usage: $0 run [OPTIONS] (<image_tag>)
Run Contrail test suite in docker container

$GREEN  -f, --feature FEATURE           $NO_COLOR Features or Tags to test - valid options are sanity, quick_sanity,
                                            ci_sanity, ci_sanity_WIP, ci_svc_sanity, upgrade, webui_sanity,
                                            ci_webui_sanity, devstack_sanity, upgrade_only. Default: sanity
$GREEN  -p, --run-path RUNPATH          $NO_COLOR Directory path on the host, in which contrail-test save all the results and other data
$GREEN  -s, --shell                     $NO_COLOR Do not run tests, but leave a shell, this is useful for debugging
$GREEN  -r, --rm	                    $NO_COLOR Remove the container on container exit, by default the container will be kept
$GREEN  -b, --background                $NO_COLOR run the container in background
$GREEN  -n, --no-color                  $NO_COLOR Disable output coloring
$GREEN  -t, --testbed TESTBED           $NO_COLOR Path to testbed file in the host,
                                            Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
$GREEN  -T, --testbed-json TESTBED_JSON $NO_COLOR Testbed json file
$GREEN  -P, --params-file PARAMS_FILE   $NO_COLOR Sanity Params ini file

NOTE: Any one of testbd or both testbed-json and params-file required

${GREEN}Possitional Parameters:

  <image_tag>       $NO_COLOR Docker image tag to run
EOF
    }

    while getopts "bhf:t:p:sknrT:P:" flag; do
        case "$flag" in
            t) testbed=$OPTARG;;
            T) testbed_json=$OPTARG;;
            P) params_file=$OPTARG;;
            f) feature=$OPTARG;;
            p) run_path=$OPTARG;;
            s) shell=1;;
            k) keep=1;;
            b) background=1;;
            r) rm=1;;
            h) usage; exit;;
            n) clear_colors ;;
        esac
    done

    shift $(( OPTIND - 1 ))
    pos_arg=$1

    image_name=$pos_arg
    check_docker
    prerun
    docker_run
}

list () {

    usage () {
        cat <<EOF

Usage: $0 list [OPTIONS]
List contrail-test containers

$GREEN  -a, --all	  $NO_COLOR affect the operations on ALL available entities
EOF
    }

    while getopts "ah" f; do
        case "$f" in
            h) usage; exit;;
            a) all=1;;
        esac
    done


# Making args for "all"
    if [[ -n $all ]]; then
        arg_list_all=" -a "
    fi
    check_docker

    # List containers
    #TODO: list in better format, list different stuffs like latest containers, failed containers, running containers, finished containers etc
    #   able to provide filters
    $docker ps $arg_list_all -f name=contrail_test_
    exit 0
}

rebuild () {
    usage () {
        cat <<EOF

Usage: $0 rebuild [OPTIONS]
Rebuild contrail-test containers

$GREEN  -f, --feature       $NO_COLOR Features or Tags to test - valid options are sanity, quick_sanity,
                                ci_sanity, ci_sanity_WIP, ci_svc_sanity, upgrade, webui_sanity,
                                ci_webui_sanity, devstack_sanity, upgrade_only. Default: sanity
$GREEN  -p, --run-path      $NO_COLOR Directory path on the host, in which contrail-test save results and other data
$GREEN  -s, --shell         $NO_COLOR Do not run tests, but leave a shell, this is useful for debugging
$GREEN  -r, --rm	        $NO_COLOR Remove the container on container exit, by default the container will be kept
$GREEN  -b, --background    $NO_COLOR run the container in background
$GREEN  -n, --no-color      $NO_COLOR Disable output coloring
$GREEN  -t, --testbed TESTBED           $NO_COLOR Path to testbed file in the host,
                                            Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
$GREEN  -T, --testbed-json TESTBED_JSON $NO_COLOR Testbed json file
$GREEN  -P, --params-file PARAMS_FILE   $NO_COLOR Sanity Params ini file

NOTE: Any one of testbd or both testbed-json and params-file required

${GREEN}Possitional Parameters:

  <container id/name>       $NO_COLOR ontainer

EOF
    }

    while getopts "bhf:t:p:sknrT:P:" flag; do
        case "$flag" in
            t) testbed=$OPTARG;;
            T) testbed_json=$OPTARG;;
            P) params_file=$OPTARG;;
            r) rm=1;;
            f) feature=$OPTARG;;
            p) run_path=$OPTARG;;
            s) shell=1;;
            k) keep=1;;
            b) background=1;;
            h) usage; exit;;
            n) clear_colors ;;
        esac
    done

    shift $(( OPTIND - 1 ))
    pos_arg=$1

    container_name=`get_container_name`
    if is_container_available; then
        green "rebuilding container - $pos_arg"
        green "This process will create an image with the container $pos_arg"
        green "Creating the image img_${container_name}"
        $docker commit $pos_arg img_${container_name}
        image_name="img_${container_name}"
    else
        red "Provided container ($pos_arg) is not available"
        exit 6
    fi
    check_docker
    prerun
    docker_run
}


## Main code Starts here

for arg in "$@"; do
    shift
    case "$arg" in
        "--help") set -- "$@" "-h" ;;
        "--testbed") set -- "$@" "-t" ;;
        "--feature") set -- "$@" "-f" ;;
        "--log-path") set -- "$@" "-p" ;;
        "--shell") set == "$@" "-s";;
        "--keep") set == "$@" "-k";;
        "--background") set == "$@" "-b";;
        "--no-color") set == "$@" "-n";;
        "--all") set == "$@" "-a" ;;
        "--testbed-json") set == "$@" "-T" ;;
        "--params-file") set == "$@" "-P" ;;
        *) set -- "$@" "$arg"
    esac
done

subcommand=$1; shift;
if [[ $subcommand == '-h' || $subcommand == '' ]]; then
    usage
    exit
else
    $subcommand $@
fi

if [ $? = 127 ]; then
    echo "Error: '$subcommand' is not a known subcommand." >&2
    echo "       Run '$0 --help' for a list of known subcommands." >&2
    exit 1
fi
