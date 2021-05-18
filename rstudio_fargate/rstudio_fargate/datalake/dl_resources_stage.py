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

from .dl_resources import DataLakeResourcesStack
from .rstudio_s3_stack import RstudioS3Stack

class DataLakeResourcesStage(core.Stage):
    def __init__(self, scope: core.Construct, id: str, pipeline_unique_id: str,
                    **kwargs):
        super().__init__(scope, id, **kwargs)

        
        instances = self.node.try_get_context("instances")

        if instances is None:
            raise ValueError("Please pass instance to use via context (dev/prod/...)")

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
        
        instance_number = len(instances.split(','))
        instances=instances.split(",")
        rstudio_account_ids=rstudio_account_ids.split(",")

        env_dict={
                    "account":self.account,
                    "region":self.region,
                }
        
        for i in range(instance_number):
            curr_instance=instances[i]
            curr_rstudio_account_id=rstudio_account_ids[i]
            dl_s3_bucket_build = DataLakeResourcesStack(self, 
               'Dl-Resources-' + curr_instance,
               curr_instance,
               curr_rstudio_account_id,
               pipeline_unique_id=pipeline_unique_id,
                env=env_dict,
            )

            s3_stack_build = RstudioS3Stack(
                self, 
                'S3-RstudioStack-' + curr_instance,
                instance=curr_instance,
                rstudio_instance_account_id=curr_rstudio_account_id,
                env=env_dict,
            ) 
        