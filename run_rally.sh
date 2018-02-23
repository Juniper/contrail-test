#!/usr/bin/env bash

source tools/common.sh

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Contrail test suite"
  echo ""
  echo "  -s, --scenarios                  List of scenarios that need to run from the scenarios directory"
  echo "  -r, --rally_cloud                Name of the rally deployment"
}

scenarios=""
scenario_dir='./rally/scenarios/'
rally_cloud='existing_cloud'
rally_dir='./rally'

if ! options=$(getopt -o s: -l scenarios: -- "$@")
then
    usage
    exit 1
fi

eval set -- $options
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit;;
    -s|--scenarios) scenarios=$2;;
    -r|--rally_cloud) rally_cloud=$2;;
  esac
  shift
done

config_file="sanity_params.ini"
contrail_fab_path='/opt/contrail/utils'

export PYTHONPATH=$PATH:$PWD:$PWD/fixtures;
prepare

#Verify rally exists, else install rally
if [ $(type rally >/dev/null 2>&1; echo $?) = 0 ]; then
        echo 'rally exists'
else
        echo 'rally doesnt exist'
        exit 1
fi

python ./rally/gen_deploy_json.py
rally deployment create --filename ${rally_dir}/existing.json --name $rally_cloud

files=""
if [[ $scenarios == "" ]]; then
    files=$(ls ${scenario_dir}/*.json)
else
    IFS=','
    for scenario in $scenarios;
    do
        if [[ -f ./rally/scenarios/${scenario}.json ]]; then
            files="$files ${scenario_dir}${scenario}.json"
        fi
    done
    IFS=' '
fi

## Pick file from the scenario directory and execute each scenarios
## Generate report in html
## store it in report location
for file in $files
do
    output=$(rally task start $file | grep -E "rally task report [0-9a-z\-]+ --out output.html" | sed 's/\t//g')
    if [[ $output != "" ]]; then
        ##rally task report <task-id> --out report/<scenario-file-name>.html
        ${output/output/report\/$(expr match "$file" '[a-z\./]*/\([a-z\-]*\).json')}
    else
        echo $file is not valid scenario
    fi
done
