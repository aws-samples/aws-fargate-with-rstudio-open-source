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

import boto3
import logging as log
import random
import string
import cfnresponse


log.getLogger().setLevel(log.INFO)

def id_generator(size, chars=string.ascii_lowercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))


def main(event, context):
    
    # This needs to change if there are to be multiple resources
    # in the same stack
    physical_id = ("%s.%s" % (id_generator(6), id_generator(16)))
    
    print(event)
    
    try:
        log.info("Input event: %s", event)

        # Check if this is a Create and we're failing Creates
        if event["RequestType"] == "Create" and event["ResourceProperties"].get(
            "FailCreate", False
        ):
            raise RuntimeError("Create failure requested")
        if event["RequestType"] in ["Create", "Update"]:
            sts_connection = boto3.client('sts')
            role = event['ResourceProperties']['AssumeRole']
            acct_b = sts_connection.assume_role(
                RoleArn=role,
                RoleSessionName="cross_acct_lambda"
            )
            
            ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
            SECRET_KEY = acct_b['Credentials']['SecretAccessKey']
            SESSION_TOKEN = acct_b['Credentials']['SessionToken']
        
            # create service client using the assumed role credentials
            client = boto3.client(
                'ssm',
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                aws_session_token=SESSION_TOKEN,
            )
            parameter_name = event['ResourceProperties']['ParameterName']
            
            parameter = client.get_parameter(Name=parameter_name, WithDecryption=True)
            print(parameter)
             
            attributes = {
                    'Response': parameter ['Parameter']['Value']
            }

            cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)

        # Do not call into STS and SSM when the resource is being deleted by CloudFormation 
        if event["RequestType"] == "Delete":
            attributes = {"Response": "Delete performed"}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)
    except Exception as e:
        log.exception(e)
        # cfnresponse's error message is always "see CloudWatch"
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_id)