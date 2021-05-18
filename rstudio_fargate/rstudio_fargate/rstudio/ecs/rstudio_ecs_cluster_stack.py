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
from aws_cdk.core import CfnOutput
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_secretsmanager as sm
import aws_cdk.aws_kms as kms
from cdk_ec2_key_pair import KeyPair

class RstudioEcsClusterStack(cdk.Stack):
        def __init__(
            self, 
            scope: cdk.Construct, 
            id: str, 
            shared_vpc: ec2.Vpc, 
            instance: str, 
            rstudio_install_type: str, 
            rstudio_ec2_instance_type: str,
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            cluster = ecs.Cluster(
                self, 
               'Rstudio-ecs-cluster-' + instance, 
                cluster_name='Rstudio-ecs-cluster-' + instance,
                vpc=shared_vpc,
                container_insights=True,  
            )   

            if rstudio_install_type == "ec2":

                
                encryption_key_arn = self.node.try_get_context("encryption_key_arn")

                if encryption_key_arn is None:
                    raise ValueError("Please provide encryption key arn")

                # encryption_key=kms.Key.from_key_arn(self, 'Encryption-Key', key_arn=encryption_key_arn)
                encryption_key=kms.Key(self, 'Encryption-Key')
                # Create the Key Pair
                keypair = KeyPair(self, "Our-Key-Pair",
                    name="instance_key_pair",
                    description="This is a Key Pair",
                    kms=encryption_key
                )
            
                auto_scaling_security_group = ec2.SecurityGroup(
                    self, 
                    'Rstudio-ec2-AutoScalingSecurityGroup-' + instance,
                    vpc=shared_vpc,
                    description='ASG Security Group -' + instance,
                )
                auto_scaling_group = autoscaling.AutoScalingGroup(
                    self, 
                    'Rstudio-ec2-ASG-' + instance,
                    vpc=shared_vpc,
                    instance_type=ec2.InstanceType(rstudio_ec2_instance_type),
                    machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
                    key_name=keypair.name,
                    min_capacity=1,
                    desired_capacity=1,
                    max_capacity=1,
                    security_group=auto_scaling_security_group,
                )

                cluster.add_auto_scaling_group(auto_scaling_group)

                CfnOutput(self, 'RstudioEC2ASGSecurityGrpId-' + instance,
                    export_name='Rstudio-EC2-ASG-Security-Group-Id-' + instance,
                    value=auto_scaling_security_group.security_group_id,
                )

            CfnOutput(self, 'RstudioClusterExport-' + instance, 
                export_name='Rstudio-Cluster-Export-' + instance,
                value=cluster.cluster_name,
            )


