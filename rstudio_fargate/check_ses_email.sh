#!/bin/bash

######################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
######################################################################################

if [ -n "$1" ]; then
  echo "Checking verification status for emails in profiles $1"
else
  echo "USAGE: ./check_ses_email.sh  <comma separated profiles of rstudio deployment accounts>"
  exit 1
fi

IFS=","
read -r -a rstudio_profiles <<< "$1"
echo "${rstudio_profiles[*]}"

users=`cat cdk.json | jq -r '.context.rstudio_users'`

IFS=","
for user in $users
do
	for profile in "$rstudio_profiles"
	do
		verif_status=`aws ses --profile "$profile" get-identity-verification-attributes --identities  "$user" |grep -o Success`


        if [ "$verif_status" != "Success" ]; then
            echo "$user" not verified in "$profile"
            jq 'del(.context.ses_email_verification_check)' cdk.json
            jq '.context += {"ses_email_verification_check": false}' cdk.json >cdk.json.tmp
            mv cdk.json.tmp cdk.json
        elif [ "$verif_status" = "Success" ]; then
            jq 'del(.context.ses_email_verification_check)' cdk.json
            jq '.context += {"ses_email_verification_check": true}' cdk.json >cdk.json.tmp
            mv cdk.json.tmp cdk.json
        fi
    done
done