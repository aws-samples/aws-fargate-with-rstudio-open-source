"""
© 2020 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.

This AWS Content is provided subject to the terms of the AWS Customer Agreement
available at http://aws.amazon.com/agreement or other written agreement between
Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

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