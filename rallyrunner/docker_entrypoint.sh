#!/usr/bin/env bash
#
# CREATE_DEP_FROM_ENV - to create rally deployment from environment variables
#   The value should be 'yes' or 'no'.
#   The variables OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_AUTH_URL,
#   OS_ENDPOINT, OS_REGION_NAME should be provided
#
# DEPLOYMENT_CONFIG_FILE - Create deployment from configuration file of the deployment.
#   Values: configuration file path which is available in the container - a volume
#       which contain the configuration file may need to be attached.
#

CREATE_DB=${CREATE_DB:-'no'}
FORCE_DB_RECREATE=${FORCE_DB_RECREATE:-'no'}
CREATE_DEP_FROM_ENV=${CREATE_DEP_FROM_ENV:-'yes'}
OS_USERNAME=${OS_USERNAME:-'admin'}
OS_TENANT_NAME=${OS_TENANT_NAME:-'admin'}
DEPLOYMENT_NAME=${DEPLOYMENT_NAME:-'cloud1'}

if [ -f /DB_CREATED ]; then
    if [ $FORCE_DB_RECREATE == 'yes' ]; then
        echo "Recreating rally db, this will wipeout all existing data from rally"
        rally-manage db recreate
    fi
elif [ ${CREATE_DB} = 'yes' ]; then
    echo "Setting up rally db"
    rally-manage db recreate
    touch /DB_CREATED
fi

if [[ ${CREATE_DEP_FROM_ENV} = 'yes' && -n ${OS_USERNAME}  && -n ${OS_PASSWORD} && -n ${OS_TENANT_NAME} && -n ${OS_AUTH_URL} ]]; then
    rally deployment create --name cluster --fromenv
fi

if [[ -n ${DEPLOYMENT_CONFIG_FILE} && -f ${DEPLOYMENT_CONFIG_FILE} ]]; then
    rally deployment create --name cluster --filename ${DEPLOYMENT_CONFIG_FILE}
fi

bash -l