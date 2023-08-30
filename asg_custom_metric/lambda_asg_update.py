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
    Duration,
    Aws,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_cloudwatch as cw,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_lambda as _lambda,
)
from constructs import Construct


class LambdaAsgUpdateStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        res_name: str,
        instance: str,
        config: list,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda role
        aws_lambda_basic_role = iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSLambdaBasicExecutionRole"
        )
        asg_role = iam.ManagedPolicy.from_aws_managed_policy_name(
            "AutoScalingFullAccess"
        )

        principal = iam.CompositePrincipal(
            iam.ServicePrincipal(service="lambda.amazonaws.com")
        )

        lambda_role = iam.Role(
            self,
            id=f"LambdaRole-{res_name}-{instance}",
            assumed_by=principal,
            managed_policies=[aws_lambda_basic_role, asg_role],
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:UpdateAutoScalingGroup",
                    "autoscaling:DeletePolicy",
                    "autoscaling:DescribePolicies",
                    "ec2:DescribeInstances",
                    "ec2:TerminateInstances",
                ],
                resources=["*"],
            )
        )

        # Lambda to update autoscaling group for enabling/disabling instance termination protection
        lambda_asg_upadte = _lambda.Function(
            self,
            f"lambda_update_asg_{res_name}_{instance}",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                one_per_az=True,
                subnet_type=getattr(ec2.SubnetType, config["asg_subnet_type"]),
            ),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="asg_handler.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(300),
            role=lambda_role,
        )

        # Setup log retention
        lambda_log_group = logs.LogGroup(
            self,
            f"lambda_update_asg_{res_name}_{instance}_log_group",
            log_group_name=f"/aws/lambda/{lambda_asg_upadte.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # Create rule to disable termination protection and scale down and  on schedule
        scale_down_rule = events.Rule(
            self,
            f"lambda_update_asg_{res_name}_{instance}_scale_down",
            schedule=events.Schedule.cron(
                minute=config["asg-scale-down"]["minute_of_day"],
                hour=config["asg-scale-down"]["hour_of_day"],
                month="*",
                week_day=config["asg-scale-down"]["day_of_week"],
                year="*",
            ),
        )

        # Create rule to scale up and enable termination protection on schedule
        scale_up_rule = events.Rule(
            self,
            f"lambda_update_asg_{res_name}_{instance}_scale_up",
            schedule=events.Schedule.cron(
                minute=config["asg-scale-up"]["minute_of_day"],
                hour=config["asg-scale-up"]["hour_of_day"],
                month="*",
                week_day=config["asg-scale-up"]["day_of_week"],
                year="*",
            ),
        )

        scale_down_rule.add_target(
            targets.LambdaFunction(
                lambda_asg_upadte,
                event=events.RuleTargetInput.from_object(
                    {
                        "region": self.region,
                        "tag_key": config["tag_name"],
                        "tag_value": config["tag_value"],
                        "scale_event": "DOWN",
                        "desired_capacity": int(
                            config["asg-scale-down"]["desired_capacity"]
                        ),
                        "min_capacity": int(config["asg-scale-down"]["min_capacity"]),
                        "max_capacity": int(config["asg-scale-down"]["max_capacity"]),
                    }
                ),
            )
        )

        scale_up_rule.add_target(
            targets.LambdaFunction(
                lambda_asg_upadte,
                event=events.RuleTargetInput.from_object(
                    {
                        "region": self.region,
                        "tag_key": config["tag_name"],
                        "tag_value": config["tag_value"],
                        "scale_event": "UP",
                        "desired_capacity": int(
                            config["asg-scale-up"]["desired_capacity"]
                        ),
                        "min_capacity": int(config["asg-scale-up"]["min_capacity"]),
                        "max_capacity": int(config["asg-scale-up"]["max_capacity"]),
                    }
                ),
            )
        )
