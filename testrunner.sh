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
##
# $TEST_RUN_CMD - this environment variable will be passed to container and this command will be used to run the test
# $EXTRA_RUN_TEST_ARGS - any extra arguments for run_tests.sh
##

docker=docker
testbed=/opt/contrail/utils/fabfile/testbeds/testbed.py
feature=sanity
run_path="${HOME}/contrail-test-runs"
arg_shell=''
name="contrail_test_$(< /dev/urandom tr -dc a-z | head -c8)"
declare -a arg_env
SCRIPT_TIMESTAMP=${SCRIPT_TIMESTAMP:-`date +"%Y_%m_%d_%H_%M_%S"`}
DEFAULT_CI_IMAGE='cirros-0.3.0-x86_64-uec'
CI_IMAGE_ORIG=${CI_IMAGE:-$DEFAULT_CI_IMAGE}
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

function have_command {
    type "$1" >/dev/null 2>/dev/null
}

try_wget () {
    wget -q --spider $1;
    return $?
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
    tag=${1:-$pos_arg}
    repo=${tag%:*}
    version=${tag#*:}
    $docker images $repo | grep -q $version
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
    arg_env[0]=" -e TEST_RUN_CMD='$TEST_RUN_CMD' -e EXTRA_RUN_TEST_ARGS='$EXTRA_RUN_TEST_ARGS' "
    n=1
    for i in `env | grep '^CT_' | sed 's/ /\|/'`; do
        var=`echo ${i/CT_/} | sed -e 's/|/ /g' -e "s/\(.*\)=\(.*\)/\1='\2'/g"`
        arg_env[$n]=" -e $var "
        n=$(($n+1))
    done
}

select_image () {
    local name
    name=${1:-$image_name}
    if [[ $name ]]; then
        if ! is_image_available $image_name; then
            red "Docker image is not available: $pos_arg"
            exit 4
        else
            image_name=$name
        fi
    else
        if [ `$docker images -q | wc -l` -eq 1 ]; then
            image_name=`$docker images --format "{{.Repository}}:{{.Tag}}"`
        else
            red "Error identifying docker image, please provide image tag found from \"$0 list -i\""
            exit 4
        fi
    fi
}

docker_run () {
    # Volumes to be mounted to container

    arg_base_vol=" -v ${run_path}/${SCRIPT_TIMESTAMP}/logs:/contrail-test/logs \
        -v ${run_path}/${SCRIPT_TIMESTAMP}/reports:/contrail-test/report \
        -v ${run_path}/${SCRIPT_TIMESTAMP}:/contrail-test.save \
        -v /etc/localtime:/etc/localtime:ro"


    if [[ -e $mount_local ]]; then
        mount_local=`readlink -f $mount_local`
        local_vol=" -v $mount_local:/contrail-test-local "
    fi
    if [[ -n $ssh_key_file ]]; then
        ssh_key_file=`readlink -f $ssh_key_file`
        if [[ -n $ssh_pub_key_file ]]; then
            ssh_pub_key_file=`readlink -f $ssh_pub_key_file`
        else
            ssh_pub_key_file="${ssh_key_file}.pub"
        fi
        if [[ -f $ssh_key_file && -f $ssh_pub_key_file ]] ; then
            key_vol=" -v $ssh_key_file:/root/.ssh/id_rsa:ro -v $ssh_pub_key_file:/root/.ssh/id_rsa.pub:ro "
        else
            echo "ERROR! provided ssh key files does not exist or not accessible"
            exit 1
        fi
    fi

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
    select_image $image_name

    # Set ci_image in case of ci
    if [[ $image_name =~ contrail-test-ci || $use_ci_image ]]; then
        ci_image_arg=" -e CI_IMAGE=$CI_IMAGE_ORIG -e ci_image=$CI_IMAGE_ORIG"
    fi

    # Run container in background
    tempfile=$(mktemp)
    if [[ -n $background ]]; then
        echo "$docker run ${arg_env[*]} $arg_base_vol $local_vol $key_vol $arg_testbed_vol $arg_testbed_json_vol $arg_params_vol --name $name $ci_image_arg -e FEATURE=$feature -d $arg_rm $arg_shell -t $image_name" > $tempfile
        id=. $tempfile
        $docker ps -a --format "ID: {{.ID}}, Name: {{.Names}}" -f id=$id
    else
        echo "$docker run ${arg_env[*]} $arg_base_vol $local_vol $key_vol $arg_testbed_vol $arg_testbed_json_vol $arg_params_vol --name $name $ci_image_arg -e FEATURE=$feature $arg_bg $arg_rm $arg_shell -t $image_name" > $tempfile
        bash $tempfile; rv=$?
	return $rv
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

$GREEN  -p, --run-path RUNPATH          $NO_COLOR Directory path on the host, in which contrail-test save all the
                                            results and other data. Default: $HOME/contrail-test-runs/
$GREEN  -s, --shell                     $NO_COLOR Do not run tests, but leave a shell, this is useful for debugging.
$GREEN  -i, --use-ci-image              $NO_COLOR Use ci image, by default it will use the image name "$DEFAULT_CI_IMAGE",
                                                  One may override this by setting the environment variable \$CI_IMAGE
$GREEN  -r, --rm	                    $NO_COLOR Remove the container on container exit, Default: Container will be kept.
$GREEN  -b, --background                $NO_COLOR run the container in background
$GREEN  -n, --no-color                  $NO_COLOR Disable output coloring
$GREEN  -t, --testbed TESTBED           $NO_COLOR Path to testbed file in the host,
                                            Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
$GREEN  -T, --testbed-json TESTBED_JSON $NO_COLOR Optional testbed json file.
$GREEN  -k, --ssh-key FILE_PATH         $NO_COLOR ssh key file path - in case of using key based ssh to cluster nodes.
                                                  Default: $HOME/.ssh/id_rsa
$GREEN  -K, --ssh-public-key FILE_PATH  $NO_COLOR ssh public key file path. Default: <ssh-key provided>.pub
$GREEN  -P, --params-file PARAMS_FILE   $NO_COLOR Optional Sanity Params ini file
$GREEN  -f, --feature FEATURE           $NO_COLOR Features or Tags to test - valid options are sanity, quick_sanity,
                                            ci_sanity, ci_sanity_WIP, ci_svc_sanity, upgrade, webui_sanity,
                                            ci_webui_sanity, devstack_sanity, upgrade_only. Default: sanity
                                            NOTE: this is only valid for Full contrail-test suite.

NOTE: Either testbed.py (-t) or both testbed-json and params-file required

${GREEN}Possitional Parameters:

  <image_tag>       $NO_COLOR Docker image tag to run (Run "$0 list -i" to list all images available)


EOF
    }

    while getopts "ibhf:t:p:sk:K:nrT:P:m:" flag; do
        case "$flag" in
            t) testbed=$OPTARG;;
            T) testbed_json=$OPTARG;;
            P) params_file=$OPTARG;;
            f) feature=$OPTARG;;
            p) run_path=$OPTARG;;
            s) shell=1;;
            i) use_ci_image=1;;
            k) ssh_key_file=$OPTARG;;
            K) ssh_pub_key_file=$OPTARG;;
            b) background=1;;
            r) rm=1;;
            h) usage; exit;;
            n) clear_colors ;;
            m) mount_local=$OPTARG;;
        esac
    done

    shift $(( OPTIND - 1 ))
    pos_arg=$1

    image_name=$pos_arg
    check_docker
    prerun
    docker_run; rv=$?
    exit $rv
}

list () {

    usage () {
        cat <<EOF

Usage: $0 list [OPTIONS]
List contrail-test containers

$GREEN  -i, --images        $NO_COLOR affect the operations on ALL available entities
$GREEN  -c, --containers    $NO_COLOR affect the operations on ALL available entities
$GREEN  -a, --all	        $NO_COLOR affect the operations on ALL available entities
EOF
    }

    while getopts "ahic" f; do
        case "$f" in
            h) usage; exit;;
            a) all=1;;
            i) images==1;;
            c) containers==1;;
        esac
    done


# Making args for "all"
    if [[ -n $all ]]; then
        arg_list_all=" -a "
    fi

    if [[ -n $images ]]; then
        list_images=1;
    elif [[ -n $containers ]]; then
        list_containers=1
    else
        list_all=1
    fi
    check_docker

    # List containers
    #TODO: list in better format, list different stuffs like latest containers, failed containers, running containers, finished containers etc
    #   able to provide filters
    if [[ -n $list_all || -n $list_images ]]; then
        echo; echo "$GREEN=========== Images =============$NO_COLOR"
        docker images  | awk 'BEGIN {printf "%-50s %-20s %-20s\n", "IMAGE","IMAGE ID", "VIRTUAL SIZE"}
                            /(contrail-test|contrail_test)/ {printf "%-50s %-20s %-20s\n", $1":"$2, $3, $(NF-1)" "$NF}'
    fi
    if [[ -n $list_all || -n $list_containers ]]; then
        echo;echo "$GREEN=========== Container Instances =============$NO_COLOR"
        $docker ps $arg_list_all -f name=contrail_test_
    fi
    exit 0
}

load () {

    usage () {
        cat <<EOF

Usage: $0 load DOCKER-IMAGE-URL
Load the docker image to local system

${GREEN}Possitional Parameters:

  <docker-image-url>       $NO_COLOR Docker image tar.gz url. Supports three modes:
                           http[s] url: example, http://myrepo/contrail-test-images/docker-image-contrail-test-ci-kilo-3.0-2709.tar.gz
                           file path: example  /root/docker-image-contrail-test-ci-kilo-3.0-2709.tar.gz

EOF
    }

    while getopts "h" f; do
        case "$f" in
            h) usage; exit;;
        esac
    done

    shift $(( OPTIND - 1 ))
    image_url=$1

    check_docker

    # Load container image
    if [[ $image_url =~ ^http[s]*:// ]]; then
        if try_wget $image_url; then
            tmp=$(mktemp -d)
            wget $image_url -O $tmp/docker-image.tar.gz
            echo "Loading the image"
            $docker load < $tmp/docker-image.tar.gz; rv=$?
        else
            echo "ERROR! $image_url is not accessible."
            exit 1
        fi
    elif [ -f $image_url ]; then
        echo "Loading the image"
        $docker load < $image_url; rv=$?
    else
        echo "ERROR: Local path $image_url is not accessible"
        exit 1
    fi

    if [ $rv -eq 0 ]; then
        echo "Successfully Loaded the image $image_url"
    else
        echo "Failed loading the image $image_url"
    fi
    exit $rv
}

rebuild () {
    usage () {
        cat <<EOF


Usage: $0 rebuild [OPTIONS] <container id/name>
Rebuild contrail-test containers

$GREEN  -p, --run-path RUNPATH          $NO_COLOR Directory path on the host, in which contrail-test save all the
                                            results and other data. Default: $HOME/contrail-test-runs/
$GREEN  -s, --shell                     $NO_COLOR Do not run tests, but leave a shell, this is useful for debugging.
$GREEN  -r, --rm	                    $NO_COLOR Remove the container on container exit, Default: Container will be kept.
$GREEN  -b, --background                $NO_COLOR run the container in background
$GREEN  -n, --no-color                  $NO_COLOR Disable output coloring
$GREEN  -t, --testbed TESTBED           $NO_COLOR Path to testbed file in the host,
                                            Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
$GREEN  -i, --use-ci-image              $NO_COLOR Use ci image, by default it will use the image name "$DEFAULT_CI_IMAGE",
                                                  One may override this by setting the environment variable \$CI_IMAGE
$GREEN  -T, --testbed-json TESTBED_JSON $NO_COLOR Optional testbed json file.
$GREEN  -P, --params-file PARAMS_FILE   $NO_COLOR Optional Sanity Params ini file
$GREEN  -k, --ssh-private-key FILE_PATH $NO_COLOR ssh private key file path - in case of using key based ssh to cluster nodes.
$GREEN  -f, --feature FEATURE           $NO_COLOR Features or Tags to test - valid options are sanity, quick_sanity,
                                            ci_sanity, ci_sanity_WIP, ci_svc_sanity, upgrade, webui_sanity,
                                            ci_webui_sanity, devstack_sanity, upgrade_only. Default: sanity
                                            NOTE: this is only valid for Full contrail-test suite.

NOTE: Either testbd.py (-t) or both testbed-json and params-file required

${GREEN}Possitional Parameters:

  <container id/name>       $NO_COLOR The container ID or name ( "$0 list -ca" to list all containers)

EOF
    }

    while getopts "ibhf:t:p:sk:nrT:P:" flag; do
        case "$flag" in
            t) testbed=$OPTARG;;
            T) testbed_json=$OPTARG;;
            P) params_file=$OPTARG;;
            i) use_ci_image=1;;
            r) rm=1;;
            f) feature=$OPTARG;;
            p) run_path=$OPTARG;;
            s) shell=1;;
            k) ssh_key_file=$OPTARG;;
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
    docker_run; rv=$?
    exit $rv
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
        "--ssh-key") set == "$@" "-k";;
        "--ssh-public-key") set == "$@" "-K";;
        "--background") set == "$@" "-b";;
        "--no-color") set == "$@" "-n";;
        "--all") set == "$@" "-a" ;;
        "--testbed-json") set == "$@" "-T" ;;
        "--params-file") set == "$@" "-P" ;;
        "--use-ci-image") set == "$@" "-i" ;;
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
