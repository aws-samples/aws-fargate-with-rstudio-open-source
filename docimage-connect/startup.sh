#!/bin/bash

set -e
set -x

# Deactivate license when it exists
deactivate() {
    echo "Deactivating license ..."
    /opt/rstudio-connect/bin/license-manager deactivate >/dev/null 2>&1
}
trap deactivate EXIT

# Activate License
RSC_LICENSE_FILE_PATH=${RSC_LICENSE_FILE_PATH:-/etc/rstudio-connect/license.lic}
if ! [ -z "$RSC_LICENSE" ]; then
    /opt/rstudio-connect/bin/license-manager activate $RSC_LICENSE
elif ! [ -z "$RSC_LICENSE_SERVER" ]; then
    /opt/rstudio-connect/bin/license-manager license-server $RSC_LICENSE_SERVER
elif test -f "$RSC_LICENSE_FILE_PATH"; then
    /opt/rstudio-connect/bin/license-manager activate-file $RSC_LICENSE_FILE_PATH
fi

CONNECT_DB_ENC_STR=`echo "$CONNECT_DB_SECRET" | /opt/rstudio-connect/bin/rscadmin configure --encrypt-config-value | tail -1`

CONNECT_DB_HOST_FIELD=`echo $CONNECT_DB_HOST | cut -d'.' -f1`

sed -i 's:CONNECT_DB_PWD:'"$CONNECT_DB_ENC_STR"':g' /etc/rstudio-connect/rstudio-connect.gcfg
sed -i 's:CONNECT_DB_HOST:'"$CONNECT_DB_HOST_FIELD"':g' /etc/rstudio-connect/rstudio-connect.gcfg
sed -i 's:CONNECT_DB_USER:'"$CONNECT_DB_USER"':g' /etc/rstudio-connect/rstudio-connect.gcfg
sed -i 's:CONNECT_DB_NAME:'"$CONNECT_DB_NAME"':g' /etc/rstudio-connect/rstudio-connect.gcfg
sed -i 's:DB_DOMAIN_SUFFIX:'"$DB_DOMAIN_SUFFIX"':g' /etc/rstudio-connect/rstudio-connect.gcfg

# ensure these cannot be inherited by child processes
unset RSC_LICENSE
unset RSC_LICENSE_SERVER
unset CONNECT_DB_PWD
unset CONNECT_DB_ENC_STR
unset CONNECT_DB_HOST_FIELD
unset CONNECT_DB_HOST
unset CONNECT_DB_USER
unset CONNECT_DB_NAME
unset DB_DOMAIN_SUFFIX

# Start RStudio Connect
/opt/rstudio-connect/bin/connect --config /etc/rstudio-connect/rstudio-connect.gcfg
