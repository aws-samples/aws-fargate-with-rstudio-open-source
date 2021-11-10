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

from aws_cdk import core as cdk

from .datasync_trigger_lambda_stack import DatasyncTriggerLambdaStack


class DataSyncTriggerLambdaStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        datalake_account_id: str,
        datalake_source_bucket_name: str,
        ssm_cross_account_lambda_role_name: str,
        datasync_task_arn_ssm_param_name: str,
        datasync_function_name: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        trigger_lambda_stack_build = DatasyncTriggerLambdaStack(
            self,
            id=f"Rstudio-Trigger-Lambda-DataSync-and-SSMRole-{instance}",
            instance=instance,
            datalake_account_id=datalake_account_id,
            datalake_source_bucket_name=datalake_source_bucket_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            datasync_task_arn_ssm_param_name=datasync_task_arn_ssm_param_name,
            datasync_function_name=datasync_function_name,
            env={
                "account": rstudio_account_id,
                "region": self.region,
            },
        )
