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
from html import escape

log.getLogger().setLevel(log.INFO)
def id_generator(size, chars=string.ascii_lowercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))
def main(event, context):
    physical_id = ("%s.%s" % (id_generator(6), id_generator(16)))
    
    print(event)
    
    try:
        log.info("Input event: %s", event)

        # Check if this is a Create and we're failing Creates
        if event["RequestType"] == "Create" and event["ResourceProperties"].get(
            "FailCreate", False
        ):
            raise RuntimeError("Create failure requested")
        if event["RequestType"] in ["Create"]:
            client = boto3.client('ses')
            sm_client = boto3.client('secretsmanager')
            email_from = event['ResourceProperties']['EmailFrom']
            email_to = event['ResourceProperties']['EmailTo']
            subject = event['ResourceProperties']['Subject']
            message = event['ResourceProperties']['Message']
            secret_arn = event['ResourceProperties']['SecretArn']
            sresponse = sm_client.get_secret_value(
                SecretId=secret_arn
            )
            message = message.replace("<password>", escape(sresponse['SecretString']))
            response = send_email(email_from, email_to,subject, message)
             
            attributes = {
                'Response': response
            }
            cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)

        if event["RequestType"] in ["Delete", "Update"]:
            attributes = {"Response": "Delete/update performed"}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, attributes, physical_id)
    except Exception as e:
        log.exception(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, physical_id)
def send_email(email_from, email_to, subject, message):
    client = boto3.client('ses')
    
    return client.send_email(
        Source=email_from,
        Destination={
            'ToAddresses': [
                email_to
            ]
        },
        Message={
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': get_text_content(message),
                    'Charset': 'UTF-8'
                },
                'Html': {
                    'Data': get_html_content(message),
                    'Charset': 'UTF-8'
                }
            }
        },
        ReplyToAddresses=[
            'no-reply@test.com',
        ]
    )
    
def get_html_content(message):
    return f"""
            <html>
              <body>
                <h1>Good day,</h1>
                 <p style="font-size:18px">{message}</p>
              </body>
            </html>
        """
    
def get_text_content(message):
    return message