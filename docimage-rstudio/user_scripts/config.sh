#!/usr/bin/with-contenv bash

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

echo "Adding environment variables to R env for Athena integration..." 

echo "ATHENA_USER=${AWS_ACCESS_KEY_ID}" >> /usr/local/lib/R/etc/Renviron
echo "ATHENA_PASSWORD=${AWS_ACCESS_KEY}" >> /usr/local/lib/R/etc/Renviron
echo "S3_BUCKET=${AWS_S3_BUCKET}" >> /usr/local/lib/R/etc/Renviron
echo "ATHENA_WG=${AWS_ATHENA_WG}" >> /usr/local/lib/R/etc/Renviron
echo "JDBC_URL='jdbc:awsathena://athena.${AWS_REGION}.amazonaws.com:443/'" >> /usr/local/lib/R/etc/Renviron

