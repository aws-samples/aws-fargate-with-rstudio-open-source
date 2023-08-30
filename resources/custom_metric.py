#!/usr/bin/python3

import os 
import sys
import boto3
import logging
import subprocess as sp
from botocore.exceptions import ClientError
from botocore.config import Config
from logging.handlers import RotatingFileHandler

#Define Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = logging.Formatter(
    "[%(asctime)s %(levelname)s] %(message)s")
file_handler = RotatingFileHandler(
    "/opt/aws/cw_custom_metric.log",
    maxBytes=1000000, 
    backupCount=10
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'
    }
)

#Setup boto clients
try:
    region = sp.getoutput("curl -ss http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region")
    cw_client = boto3.client("cloudwatch", region_name=region, config=config)
    asg_client = boto3.client("autoscaling", region_name=region, config=config)
except ClientError as e:
    raise Exception(f"An error occurred setting up boto clients: {e}")

#Upload metric data
def put_metric_data(asg_name, inst_id, metric_data):
    try:
        logger.info("Uploading metric data to CW")
        cw_client.put_metric_data(
            Namespace="##NAME_SPACE##",
            MetricData=[
                {
                    "MetricName": "##METRIC_NAME##",
                    "Dimensions": [
                        {"Name": "##DIMENSION_NAME##", "Value": "##DIMENSION_VALUE##"}
                    ],
                    #"Timestamp": datetime.datetime.now(),
                    "Value": int(metric_data),
                    "Unit": "Count",
                },
            ],
        )
    except ClientError as e:
        raise Exception(f"An error occurred uploading data to cw: {e}")
    logger.info(f"Uploaded metric data to CW from asg: {asg_name}; instance id: {inst_id}; value: {metric_data}") 

#Main
def main():

    logger.info("Getting instance id")
    inst_id = sp.getoutput("curl -s http://169.254.169.254/latest/meta-data/instance-id")
    
    logger.info("Getting ASG name from instance id")

    #Get ASG
    try:
        result = asg_client.describe_auto_scaling_instances(
            InstanceIds=[inst_id,],
            MaxRecords=1
        )
    except ClientError as e:
        raise Exception(f"An error occurred getting ASG name: {e}")

    asg_name = result["AutoScalingInstances"][0]["AutoScalingGroupName"]
    logger.info(f"Found ASG: {asg_name}")
    
    logger.info("Getting custom metric value for upload")
    metric_data = sp.getoutput("/usr/sbin/ss -tnH src :##PORT## | wc -l")
    logger.info("Publishing cloudwatch metrics")

    #Check if cron should be disabled if one value above threshold is uploaded. Upload value if it below threshold
    enable_flag = sp.getoutput("crontab -l | grep /opt/aws/custom_metric.py")
    if int(metric_data) <= ##THRESHOLD##:
        if "DISABLE" in enable_flag:
            logger.info("Enabling metric value upload in cron as the metric value is below threshold: ##THRESHOLD##")
            os.system("crontab -l > /opt/aws/crontab.old")
            os.system("cp /opt/aws/crontab.old /opt/aws/crontab.new")
            os.system("sed -i 's/custom_metric.py DISABLE/custom_metric.py ENABLE/gi' /opt/aws/crontab.new")
            os.system("crontab < /opt/aws/crontab.new")
            logger.info("Enabled metric value upload in cron")
        put_metric_data(asg_name, inst_id, metric_data)
    elif int(metric_data) > ##THRESHOLD##:
        if "ENABLE" in enable_flag:
            put_metric_data(asg_name, inst_id, metric_data)
            logger.info("Disabling metric value upload for threshold breach in cron as connection count reached above threshold: ##THRESHOLD##")
            os.system("crontab -l > /opt/aws/crontab.old")
            os.system("cp /opt/aws/crontab.old /opt/aws/crontab.new")
            os.system("sed -i 's/custom_metric.py ENABLE/custom_metric.py DISABLE/gi' /opt/aws/crontab.new")
            os.system("crontab < /opt/aws/crontab.new")
            logger.info("Disabled metric value upload for threshold breach in cron")
        else:
            logger.info("Not uploading metric value to CW as it is above threshold: ##THRESHOLD## and has been uploaded once already")

main()