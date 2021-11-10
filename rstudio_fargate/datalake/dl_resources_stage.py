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

This stack creates the pipeline stage for deployment into central data account

"""

from aws_cdk import core
from aws_cdk import core as cdk

from .dl_resources import DataLakeResourcesStack
from .rstudio_s3_stack import RstudioS3Stack


class DataLakeResourcesStage(core.Stage):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        datalake_source_bucket_name: str,
        athena_output_bucket_name: str,
        athena_output_bucket_key: str,
        athena_workgroup_name: str,
        s3_lifecycle_expiration_duration: int,
        s3_trasnition_duration_infrequent_access: int,
        s3_trasnition_duration_glacier: int,
        ssm_cross_account_role_name: str,
        datalake_source_bucket_key_hourly: str,
        datalake_source_bucket_key_instant: str,
        lambda_datasync_trigger_function_arn: str,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        env_dict = {
            "account": self.account,
            "region": self.region,
        }

        dl_s3_bucket_build = DataLakeResourcesStack(
            self,
            id=f"Dl-Resources-{instance}",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            datalake_source_bucket_name=datalake_source_bucket_name,
            datalake_source_bucket_key_hourly=datalake_source_bucket_key_hourly,
            datalake_source_bucket_key_instant=datalake_source_bucket_key_instant,
            lambda_datasync_trigger_function_arn=lambda_datasync_trigger_function_arn,
            env=env_dict,
        )

        s3_stack_build = RstudioS3Stack(
            self,
            id=f"S3-RstudioStack-{instance}",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            athena_output_bucket_name=athena_output_bucket_name,
            athena_workgroup_name=athena_workgroup_name,
            athena_output_bucket_key=athena_output_bucket_key,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            s3_lifecycle_expiration_duration=s3_lifecycle_expiration_duration,
            s3_trasnition_duration_infrequent_access=s3_trasnition_duration_infrequent_access,
            s3_trasnition_duration_glacier=s3_trasnition_duration_glacier,
            env=env_dict,
        )
