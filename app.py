#!/usr/bin/env python3

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

import os
import json

from aws_cdk import core as cdk
from aws_cdk.core import App, Aspects
from cdk_nag import AwsSolutionsChecks
from rstudio_fargate.rstudio_pipeline_stack import RstudioPipelineStack

app = cdk.App()

# Aspects.of(app).add(AwsSolutionsChecks())

env = cdk.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

instance = app.node.try_get_context("instance")

if instance is None:
    raise ValueError("Please pass instance to use via context (dev/prod/...)")

rstudio_account_id = app.node.try_get_context("rstudio_account_id")

if rstudio_account_id is None:
    raise ValueError("Please supply aws account id of the rstudio deployment account")

rstudio_pipeline_account_id = app.node.try_get_context("rstudio_pipeline_account_id")

if rstudio_pipeline_account_id is None:
    raise ValueError("Please supply the central development account id")

network_account_id = app.node.try_get_context("network_account_id")

if network_account_id is None:
    raise ValueError("Please supply the central network account id")

datalake_account_id = app.node.try_get_context("datalake_account_id")

if datalake_account_id is None:
    raise ValueError("Please supply the central data account id")

datalake_aws_region = app.node.try_get_context("datalake_aws_region")

if datalake_aws_region is None:
    raise ValueError("Please provide datalake account region")

code_repo_name = app.node.try_get_context("code_repo_name")

if code_repo_name is None:
    raise ValueError("Please provide rstudio/shiny code repository name")

r53_base_domain = app.node.try_get_context("r53_base_domain")

if r53_base_domain is None:
    raise ValueError("Please provide base route 53 domain for the build")

rstudio_install_type = app.node.try_get_context("rstudio_install_type")

if rstudio_install_type is None:
    raise ValueError("Please provide rstudio installation type ....ec2 or fargate ...")

rstudio_ec2_instance_type = app.node.try_get_context("rstudio_ec2_instance_type")

if rstudio_ec2_instance_type is None:
    raise ValueError("Please provide ec2 instance type for ECS cluster")

rstudio_container_memory_in_gb = int(
    app.node.try_get_context("rstudio_container_memory_in_gb")
)

if rstudio_container_memory_in_gb is None:
    raise ValueError("Please pass rstudio container memory for your install type")

number_of_rstudio_containers = int(
    app.node.try_get_context("number_of_rstudio_containers")
)

if number_of_rstudio_containers is None:
    raise ValueError("Please provide number of rstudio containers to deploy")

vpc_cidr_range = app.node.try_get_context("vpc_cidr_range")

if vpc_cidr_range is None:
    raise ValueError("Please provide vpc cidr range for the build")

allowed_ips = app.node.try_get_context("allowed_ips")

if allowed_ips is None:
    print(
        "List of allowed IP addresses is not provided, will default to ALLOW all IPs through the WAf for rstudio/shiny"
    )

sns_email = app.node.try_get_context("sns_email_id")

if sns_email is None:
    raise ValueError(
        "Please provide email id for sending pipeline failure notifications"
    )

datalake_source_bucket_name = app.node.try_get_context("datalake_source_bucket_name")

if datalake_source_bucket_name is None:
    raise ValueError("Please supply prefix for the data upload bucket")

datalake_source_bucket_name = f"{datalake_source_bucket_name}-{instance}"
athena_output_bucket_name = f"{datalake_source_bucket_name}-athena-output-{instance}"
athena_workgroup_name = f"rstudio-wg-{instance}"
datasync_function_name = f"trigger-datasync-task-{instance}"
lambda_datasync_trigger_function_arn = f"arn:aws:lambda:{env.region}:{rstudio_account_id}:function:{datasync_function_name}"
datasync_task_arn_ssm_param_name = f"/{instance}/rstudio-datasync-taskarn"
ssm_cross_account_role_name = f"ssm-cross-account-role-{instance}"
ssm_cross_account_lambda_role_name = f"get-ssm-parameter-lambda-role-{instance}"
rstudio_container_repository_name = f"{code_repo_name}_rstudio_image_{instance}"
shiny_container_repository_name = f"{code_repo_name}_shiny_image_{instance}"
rstudio_container_repository_name_ssm_param = f"/rstudio/repo/name/{instance}"
rstudio_container_repository_arn_ssm_param = f"/rstudio/repo/arn/{instance}"
shiny_container_repository_name_ssm_param = f"/shiny/repo/name/{instance}"
shiny_container_repository_arn_ssm_param = f"/shiny/repo/arn/{instance}"
ssm_route53_delegation_name = f"/{instance}/hosted-zone-name"
ssm_route53_delegation_id = f"/{instance}/hosted-zone-id"
r53_delegation_role_name = f"DnsDelegation-Rstudio-{instance}"
ecs_cluster_name = f"Rstudio-Shiny-ecs-cluster-{instance}"
rstudio_cwlogs_key_alias = f"alias/cwlogs-rstudio-{instance}"
shiny_cwlogs_key_alias = f"alias/cwlogs-shiny-{instance}"
rstudio_efs_key_alias = f"alias/efs-rstudio-{instance}"
shiny_efs_key_alias = f"alias/efs-shiny-{instance}"
rstudio_user_key_alias = f"alias/rstudio-user-{instance}"

with open("parameters.json", "r") as param_file:
    param_data = param_file.read()

param_vals = json.loads(param_data)

docker_secret_name = param_vals["Parameters"]["docker_secret_name"]
asg_min_capacity = int(param_vals["Parameters"]["asg_min_capacity"])
asg_desired_capacity = int(param_vals["Parameters"]["asg_desired_capacity"])
asg_max_capacity = int(param_vals["Parameters"]["asg_max_capacity"])
shiny_min_capacity = int(param_vals["Parameters"]["shiny_min_capacity"])
shiny_desired_capacity = int(param_vals["Parameters"]["shiny_desired_capacity"])
shiny_max_capacity = int(param_vals["Parameters"]["shiny_max_capacity"])
shiny_container_memory_in_gb = int(
    param_vals["Parameters"]["shiny_container_memory_in_gb"]
)
rstudio_container_memory_reserved = int(
    param_vals["Parameters"]["rstudio_container_memory_reserved"]
)
rstudio_health_check_grace_period = int(
    param_vals["Parameters"]["rstudio_health_check_grace_period"]
)
shiny_health_check_grace_period = int(
    param_vals["Parameters"]["shiny_health_check_grace_period"]
)
shiny_cookie_stickiness_duration = int(
    param_vals["Parameters"]["shiny_cookie_stickiness_duration"]
)
shiny_scale_in_cooldown = int(param_vals["Parameters"]["shiny_scale_in_cooldown"])
shiny_scale_out_cooldown = int(param_vals["Parameters"]["shiny_scale_out_cooldown"])
shiny_cpu_target_utilization_percent = int(
    param_vals["Parameters"]["shiny_cpu_target_utilization_percent"]
)
shiny_memory_target_utilization_percent = int(
    param_vals["Parameters"]["shiny_memory_target_utilization_percent"]
)
shiny_requests_per_target = int(param_vals["Parameters"]["shiny_requests_per_target"])
datalake_source_bucket_key_hourly = param_vals["Parameters"][
    "datalake_source_bucket_key_hourly"
]
access_point_path_hourly = param_vals["Parameters"]["access_point_path_hourly"]
datalake_source_bucket_key_instant = param_vals["Parameters"][
    "datalake_source_bucket_key_instant"
]
access_point_path_instant = param_vals["Parameters"]["access_point_path_instant"]
athena_output_bucket_key = param_vals["Parameters"]["athena_output_bucket_key"]
s3_lifecycle_expiration_duration = int(
    param_vals["Parameters"]["s3_lifecycle_expiration_duration"]
)
s3_trasnition_duration_infrequent_access = int(
    param_vals["Parameters"]["s3_trasnition_duration_infrequent_access"]
)
s3_trasnition_duration_glacier = int(
    param_vals["Parameters"]["s3_trasnition_duration_glacier"]
)
home_container_path = param_vals["Parameters"]["home_container_path"]
shiny_share_container_path = param_vals["Parameters"]["shiny_share_container_path"]
hourly_sync_container_path = param_vals["Parameters"]["hourly_sync_container_path"]
instant_sync_container_path = param_vals["Parameters"]["instant_sync_container_path"]

rstudio_pipeline_build = RstudioPipelineStack(
    app,
    id=f"Rstudio-Pipeline-Stack-{instance}",
    instance=instance,
    rstudio_account_id=rstudio_account_id,
    rstudio_pipeline_account_id=rstudio_pipeline_account_id,
    network_account_id=network_account_id,
    datalake_account_id=datalake_account_id,
    datalake_aws_region=datalake_aws_region,
    code_repo_name=code_repo_name,
    r53_base_domain=r53_base_domain,
    rstudio_install_type=rstudio_install_type,
    rstudio_ec2_instance_type=rstudio_ec2_instance_type,
    rstudio_container_memory_in_gb=int(rstudio_container_memory_in_gb),
    number_of_rstudio_containers=int(number_of_rstudio_containers),
    vpc_cidr_range=vpc_cidr_range,
    allowed_ips=allowed_ips,
    sns_email=sns_email,
    datalake_source_bucket_name=datalake_source_bucket_name,
    athena_output_bucket_name=athena_output_bucket_name,
    athena_workgroup_name=athena_workgroup_name,
    lambda_datasync_trigger_function_arn=lambda_datasync_trigger_function_arn,
    ssm_cross_account_role_name=ssm_cross_account_role_name,
    ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
    datasync_task_arn_ssm_param_name=datasync_task_arn_ssm_param_name,
    datasync_function_name=datasync_function_name,
    rstudio_container_repository_name=rstudio_container_repository_name,
    shiny_container_repository_name=shiny_container_repository_name,
    rstudio_container_repository_name_ssm_param=rstudio_container_repository_name_ssm_param,
    rstudio_container_repository_arn_ssm_param=rstudio_container_repository_arn_ssm_param,
    shiny_container_repository_name_ssm_param=shiny_container_repository_name_ssm_param,
    shiny_container_repository_arn_ssm_param=shiny_container_repository_arn_ssm_param,
    ssm_route53_delegation_name=ssm_route53_delegation_name,
    ssm_route53_delegation_id=ssm_route53_delegation_id,
    r53_delegation_role_name=r53_delegation_role_name,
    ecs_cluster_name=ecs_cluster_name,
    rstudio_cwlogs_key_alias=rstudio_cwlogs_key_alias,
    shiny_cwlogs_key_alias=shiny_cwlogs_key_alias,
    rstudio_efs_key_alias=rstudio_efs_key_alias,
    shiny_efs_key_alias=shiny_efs_key_alias,
    rstudio_user_key_alias=rstudio_user_key_alias,
    docker_secret_name=docker_secret_name,
    asg_min_capacity=asg_min_capacity,
    asg_desired_capacity=asg_desired_capacity,
    asg_max_capacity=asg_max_capacity,
    shiny_min_capacity=shiny_min_capacity,
    shiny_desired_capacity=shiny_desired_capacity,
    shiny_max_capacity=shiny_max_capacity,
    shiny_container_memory_in_gb=shiny_container_memory_in_gb,
    rstudio_container_memory_reserved=rstudio_container_memory_reserved,
    rstudio_health_check_grace_period=rstudio_health_check_grace_period,
    shiny_health_check_grace_period=shiny_health_check_grace_period,
    shiny_cookie_stickiness_duration=shiny_cookie_stickiness_duration,
    shiny_scale_in_cooldown=shiny_scale_in_cooldown,
    shiny_scale_out_cooldown=shiny_scale_out_cooldown,
    shiny_cpu_target_utilization_percent=shiny_cpu_target_utilization_percent,
    shiny_memory_target_utilization_percent=shiny_memory_target_utilization_percent,
    shiny_requests_per_target=shiny_requests_per_target,
    datalake_source_bucket_key_hourly=datalake_source_bucket_key_hourly,
    access_point_path_hourly=access_point_path_hourly,
    datalake_source_bucket_key_instant=datalake_source_bucket_key_instant,
    access_point_path_instant=access_point_path_instant,
    athena_output_bucket_key=athena_output_bucket_key,
    s3_lifecycle_expiration_duration=s3_lifecycle_expiration_duration,
    s3_trasnition_duration_infrequent_access=s3_trasnition_duration_infrequent_access,
    s3_trasnition_duration_glacier=s3_trasnition_duration_glacier,
    home_container_path=home_container_path,
    shiny_share_container_path=shiny_share_container_path,
    hourly_sync_container_path=hourly_sync_container_path,
    instant_sync_container_path=instant_sync_container_path,
    env=env,
)

app.synth()
