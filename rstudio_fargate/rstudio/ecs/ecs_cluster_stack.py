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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_autoscaling as autoscaling,
    aws_kms as kms,
)


class EcsClusterStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        instance: str,
        rstudio_install_type: str,
        rstudio_ec2_instance_type: str,
        ecs_cluster_name: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        cluster_security_group = ec2.SecurityGroup(
            self,
            id=f"Rstudio-SecurityGroup-{instance}",
            vpc=vpc,
            description=f"Rstudio Security Group - {instance}",
        )

        cluster = ecs.Cluster(
            self,
            id=f"Rstudio-Shiny-ecs-cluster-{instance}",
            cluster_name=ecs_cluster_name,
            vpc=vpc,
            container_insights=True,
        )

        if rstudio_install_type == "ec2":

            auto_scaling_group = autoscaling.AutoScalingGroup(
                self,
                id="Rstudio-ec2-ASG-" + instance,
                vpc=vpc,
                instance_type=ec2.InstanceType(rstudio_ec2_instance_type),
                machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
                min_capacity=asg_min_capacity,
                desired_capacity=asg_desired_capacity,
                max_capacity=asg_max_capacity,
                security_group=cluster_security_group,
            )

            cluster_capacity_provider = ecs.AsgCapacityProvider(
                self,
                id=f"RstudioCapacityProvider-{instance}",
                capacity_provider_name=f"Rstudio-Capacity-Provider-{instance}",
                auto_scaling_group=auto_scaling_group,
                target_capacity_percent=100,
                enable_managed_termination_protection=False,
            )

            cluster.add_asg_capacity_provider(
                cluster_capacity_provider
            )

        self.ecs_cluster_security_group_id = cluster_security_group.security_group_id
        self.ecs_cluster_name = cluster.cluster_name
