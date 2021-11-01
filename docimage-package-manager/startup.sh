#!/bin/bash

set -e
set -x

# Deactivate license when it exists
deactivate() {
    echo "Deactivating license ..."
    /opt/rstudio-pm/bin/license-manager deactivate >/dev/null 2>&1
}
trap deactivate EXIT

# Activate License
RSPM_LICENSE_FILE_PATH=${RSPM_LICENSE_FILE_PATH:-/etc/rstudio-pm/license.lic}
if ! [ -z "$RSPM_LICENSE" ]; then
    /opt/rstudio-pm/bin/license-manager activate $RSPM_LICENSE
elif ! [ -z "$RSPM_LICENSE_SERVER" ]; then
    /opt/rstudio-pm/bin/license-manager license-server $RSPM_LICENSE_SERVER
elif test -f "$RSPM_LICENSE_FILE_PATH"; then
    /opt/rstudio-pm/bin/license-manager activate-file $RSPM_LICENSE_FILE_PATH
fi

PM_DB_ENC_STR=`echo "$PM_DB_SECRET" | rspm encrypt | tail -1`
USAGE_DB_ENC_STR=`echo "$PM_USAGE_DB_SECRET" | rspm encrypt | tail -1`

PM_DB_HOST_FIELD=`echo $PM_DB_HOST | cut -d'.' -f1`
PM_USAGE_DB_HOST_FIELD=`echo $PM_USAGE_DB_HOST | cut -d'.' -f1`

sed -i 's:PM_DB_PWD:'"$PM_DB_ENC_STR"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_DB_HOST:'"$PM_DB_HOST_FIELD"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_DB_USER:'"$PM_DB_USER"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_DB_NAME:'"$PM_DB_NAME"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:DB_DOMAIN_SUFFIX:'"$DB_DOMAIN_SUFFIX"':g' /etc/rstudio-pm/rstudio-pm.gcfg

sed -i 's:USAGE_DB_PWD:'"$USAGE_DB_ENC_STR"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_USAGE_DB_HOST:'"$PM_USAGE_DB_HOST_FIELD"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_USAGE_DB_USER:'"$PM_USAGE_DB_USER"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:PM_USAGE_DB_NAME:'"$PM_USAGE_DB_NAME"':g' /etc/rstudio-pm/rstudio-pm.gcfg
sed -i 's:DB_DOMAIN_SUFFIX:'"$DB_DOMAIN_SUFFIX"':g' /etc/rstudio-pm/rstudio-pm.gcfg

# ensure these cannot be inherited by child processes
unset RSPM_LICENSE
unset RSPM_LICENSE_SERVER
unset PM_DB_ENC_STR
unset USAGE_DB_ENC_STR
unset PM_DB_SECRET
unset PM_USAGE_DB_SECRET
unset PM_DB_HOST
unset PM_DB_USER
unset PM_DB_NAME
unset PM_USAGE_DB_HOST
unset PM_USAGE_DB_USER
unset PM_USAGE_DB_NAME
unset DB_DOMAIN_SUFFIX

# Start RStudio Package Manager
/opt/rstudio-pm/bin/rstudio-pm --config /etc/rstudio-pm/rstudio-pm.gcfg