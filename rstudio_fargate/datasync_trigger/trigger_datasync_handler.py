"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import json
import boto3
import os

datasync_task_arn_param_name = os.environ["DATASYNC_TASK_ARN_SSM_PARAM_NAME"]

# Let's use Amazon Datasync
datasync = boto3.client("datasync")
ssm = boto3.client("ssm")


def lambda_handler(event, context):
    objectKey = ""
    datasync_task_arn = ""

    print(event)

    try:
        objectKey = event["Records"][0]["s3"]["object"]["key"]
    except KeyError:
        raise KeyError(
            "Received invalid event - unable to locate Object key to upload.", event
        )

    try:
        parameter = ssm.get_parameter(
            Name=datasync_task_arn_param_name, WithDecryption=True
        )
        print(parameter)
        datasync_task_arn = parameter["Parameter"]["Value"]
    except ValueError:
        raise ValueError(
            f"Unable to locate value for parameter {datasync_task_arn_param_name}.",
            event,
        )

    response = datasync.start_task_execution(
        TaskArn=datasync_task_arn,
        OverrideOptions={},
        Includes=[
            {"FilterType": "SIMPLE_PATTERN", "Value": "/" + os.path.basename(objectKey)}
        ],
    )

    return {"response": response}
