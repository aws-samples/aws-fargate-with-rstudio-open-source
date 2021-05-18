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

from aws_cdk import core
from aws_cdk import core as cdk

from .rstudio_trigger_lambda_stack import RstudioTriggerLambdaStack

class RstudioPipelineLambdaStage(core.Stage):
    def __init__(self, scope: core.Construct, 
        id: str,
        pipeline_unique_id:str,
        **kwargs):
        super().__init__(scope, id, **kwargs)

        instances = self.node.try_get_context("instances")

        if instances is None:
            raise ValueError("Please pass instance to use via context (dev/prod/...)")

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
            
        # Build docker images and publish them to ECR repositories in the rstudio pipeline account
        env_dict={
                "account":self.account,
                "region":self.region,
            }
        
         
        instance_number = len(instances.split(','))
        instances=instances.split(",")
        rstudio_account_ids=rstudio_account_ids.split(",")
        
        for i in range(instance_number):
            instance=instances[i]
            rstudio_account_id=rstudio_account_ids[i]
            trigger_lambda_stack_build = RstudioTriggerLambdaStack(
                self, 
                "Rstudio-Trigger-Lambda-DataSync-and-SSMRole" + instance,
                instance=instance,
                pipeline_unique_id=pipeline_unique_id,
                env={
                    "account":rstudio_account_id,
                    "region":self.region,
                }
            )
