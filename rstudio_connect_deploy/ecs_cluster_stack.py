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

from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_autoscaling as autoscaling,
    aws_secretsmanager as sm,
    aws_kms as kms,
)


class EcsClusterStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        vpc: ec2.Vpc,
        ec2_instance_type: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        connect_pm_cluster = ecs.Cluster(
            self,
            id=f"RSC-RSPM-ecs-cluster-{instance}",
            cluster_name=f"RSC-RSPM-ecs-cluster-{instance}",
            vpc=vpc,
            container_insights=True,
        )

        connect_pm_auto_scaling_security_group = ec2.SecurityGroup(
            self,
            id=f"RSC_RSPM-AutoScalingSecurityGroup-{instance}",
            vpc=vpc,
            description=f"RSC-RSPM ASG Security Group - {instance}",
        )

        connect_pm_auto_scaling_group = autoscaling.AutoScalingGroup(
            self,
            id=f"RSC-RSPM-ec2-ASG-{instance}",
            vpc=vpc,
            instance_type=ec2.InstanceType(ec2_instance_type),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=asg_min_capacity,
            desired_capacity=asg_desired_capacity,
            max_capacity=asg_max_capacity,  # Increase max capacity number in parameters.json to scale out the number of EC2 instances in the ASG
            security_group=connect_pm_auto_scaling_security_group,
        )

        connect_pm_cluster_capacity_provider = ecs.AsgCapacityProvider(
            self,
            id=f"RSCRSPMAsgCapacityProvider-{instance}",
            capacity_provider_name=f"RSC-RSPM-Caapcity-Provider-{instance}",
            auto_scaling_group=connect_pm_auto_scaling_group,
            target_capacity_percent=100,
            enable_managed_termination_protection=False,
        )

        connect_pm_cluster.add_asg_capacity_provider(
            connect_pm_cluster_capacity_provider
        )

        # Pass stack variables to other stacks

        self.ecs_cluster_name = connect_pm_cluster.cluster_name
        self.ecs_cluster_security_group_id = (
            connect_pm_auto_scaling_security_group.security_group_id
        )
