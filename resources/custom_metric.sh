#!/bin/bash

### Get number of TCP connections (established, waiting, idle - all states) on CSM or FO Partition port
### Create a custom cloudwatch metric with the value
### Push to cloudwatch runs from cron

#Get the instance and asg ids.
REGION=`curl -ss http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region`

INST_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
ASG_ID=$(aws autoscaling describe-auto-scaling-instances --instance-ids $INST_ID --region $REGION | grep AutoScalingGroupName | cut -d'"' -f 4)

# Get number of TCP connections on port
function getTcpConns {
  /usr/sbin/ss -tnH src :##PORT## | wc -l
}

METRIC_DATA=`getTcpConns`

#Push metric to cloudwatch
aws cloudwatch put-metric-data --region $REGION --metric-name ##METRIC_NAME## \
--unit Count --value $METRIC_DATA --dimensions ##dimension_name##=$ASG_ID --namespace ##NAME_SPACE##
