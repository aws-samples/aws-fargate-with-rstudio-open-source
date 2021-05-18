"""
� 2020 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.

This AWS Content is provided subject to the terms of the AWS Customer Agreement
available at http://aws.amazon.com/agreement or other written agreement between
Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

"""

import json
import boto3
import os

# Let's use Amazon Datasync
datasync = boto3.client('datasync')
ssm = boto3.client('ssm')
            
def lambda_handler(event, context):
    objectKey = ''
    datasync_task_arn=''
    
    try:
        objectKey = event["Records"][0]["s3"]["object"]["key"]
    except KeyError:
        raise KeyError("Received invalid event - unable to locate Object key to upload.", event)
    
    try:
        parameter = ssm.get_parameter(Name='/rstudio/datasync_task_arn', WithDecryption=True)
        print(parameter)
        datasync_task_arn=parameter ['Parameter']['Value']
    except ValueError:
        raise ValueError("Unable to locate value for parameter /rstudio/datasync_task_arn.", event)
    
    response = datasync.start_task_execution(
        TaskArn=datasync_task_arn,
        OverrideOptions={
        },
        Includes=[
            {
                'FilterType': 'SIMPLE_PATTERN',
                'Value': '/' + os.path.basename(objectKey)
            }
        ]
    )
    
    return {
        'response' : response
    }
