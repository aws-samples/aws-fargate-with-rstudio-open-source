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
from aws_cdk.core import Fn, RemovalPolicy,Duration,CfnOutput
from aws_cdk import aws_secretsmanager as sm
import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms

class RstudioConfigurationStack(cdk.Stack):
        def __init__(
            self, 
            scope: cdk.Construct, 
            id: str, 
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            instances = self.node.try_get_context("instances")

            if instances is None:
                raise ValueError("Please pass instance to use via context (dev/prod/...)")
    
            rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")
    
            if rstudio_account_ids is None:
                raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
            
            # Add resource policies to allow all rstudio accounts to use this CMK
            instance_number = len(instances.split(','))
            instances=instances.split(",")
            rstudio_account_ids=rstudio_account_ids.split(",")
        
            role_principals = []
            
            for i in range(instance_number):
                instance=instances[i]
                rstudio_account_id=rstudio_account_ids[i]
            
                role_principals.append(
                    iam.AccountPrincipal(rstudio_account_id)
                )
                
            rstudio_kms_key = kms.Key(
                self,
                'Rstudio-Kms-Key',      
                enable_key_rotation= True,
                alias= 'alias/rstudio-kms-key',
                removal_policy=RemovalPolicy.DESTROY
            )

            rstudio_kms_key.add_to_resource_policy(
                statement=iam.PolicyStatement(
                    actions=[
                        "kms:Decrypt",
                        "kms:DescribeKey",
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "kms:GenerateDataKey*"
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=['*'],
                    principals=role_principals
                )
            )
            
            
            CfnOutput(self, 'Rstudio-Kms-Key-Arn', 
                export_name='Rstudio-Kms-Key-Arn',
                value=rstudio_kms_key.key_arn,
            )