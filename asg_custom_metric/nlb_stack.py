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
    Stack,
    Tags,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_cloudwatch as cw,
)
from constructs import Construct


class NlbStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        instance: str,
        vpc: ec2.Vpc,
        res_name: str,
        config: list,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Creating bucket for NLB Access Logs
        nlb_logs_bucket = s3.Bucket(
            self, f"{res_name}-nlb-logs-{self.stack_name}-{instance}"
        )

        # Creates the Network Load Balancer
        lb = elbv2.NetworkLoadBalancer(
            self,
            f"{res_name}-NLB-{instance}",
            vpc=vpc,
            load_balancer_name=f"{res_name}-NLB-{instance}-internal",
            cross_zone_enabled=True,
            internet_facing=False,
        )

        # Enables Access Logs
        lb.log_access_logs(nlb_logs_bucket)

        # Add tags
        Tags.of(lb).add("Stack", self.stack_name)

        # Pass LB to ASG stack
        self.lb_arn = lb.load_balancer_arn
        self.lb_dns = lb.load_balancer_dns_name
