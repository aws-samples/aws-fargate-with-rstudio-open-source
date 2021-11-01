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
from rstudio_connect_deploy.pipeline_stack import PipelineStack

app = cdk.App()

instance = app.node.try_get_context("instance")

if instance is None:
    raise ValueError("Please pass instance to use via context (dev/prod/...)")

r53_base_domain = app.node.try_get_context("r53_base_domain")

if r53_base_domain is None:
    raise ValueError(
        "Please pass the public route53 base domain to be used for building RSC/RSPM URLs. This domain must exist in your AWS account as a public hosted zone."
    )

code_repo_name = app.node.try_get_context("code_repo_name")

if code_repo_name is None:
    raise ValueError("Please provide connect code repository name")

ec2_instance_type = app.node.try_get_context("ec2_instance_type")

if ec2_instance_type is None:
    raise ValueError("Please pass ec2 instance type for the ECS cluster")

vpc_cidr = app.node.try_get_context("vpc_cidr_range")

if vpc_cidr is None:
    raise ValueError("Please provide vpc cidr range for the build")

allowed_ips = app.node.try_get_context("allowed_ips")

if allowed_ips is None:
    print("List of allowed IP addresses is not provided, will default to ALLOW all IPs")

sns_email = app.node.try_get_context("sns_email_id")

if sns_email is None:
    raise ValueError(
        "Please provide email id for sending pipeline failure notifications"
    )

connect_cwlogs_key_alias = f"alias/cwlogs-connect-{instance}"
packagae_cwlogs_key_alias = f"alias/cwlogs-package-{instance}"
connect_efs_key_alias = f"alias/efs-connect-{instance}"
package_efs_key_alias = f"alias/efs-package-{instance}"
connect_db_key_alias = f"alias/rds-connect-{instance}"
package_db_key_alias = f"alias/rds-package-{instance}"
connect_repository_name = f"{code_repo_name}_connect_image_{instance}"
package_repository_name = f"{code_repo_name}_package_image_{instance}"

with open("parameters.json", "r") as param_file:
    param_data = param_file.read()

param_vals = json.loads(param_data)

db_domain_suffix = param_vals["Parameters"]["db_domain_suffix"]
docker_secret_name = param_vals["Parameters"]["docker_secret_name"]
rsc_license_key_secret_name = param_vals["Parameters"]["rsc_license_key_secret_name"]
rspm_license_key_secret_name = param_vals["Parameters"]["rspm_license_key_secret_name"]
asg_min_capacity = int(param_vals["Parameters"]["asg_min_capacity"])
asg_desired_capacity = int(param_vals["Parameters"]["asg_desired_capacity"])
asg_max_capacity = int(param_vals["Parameters"]["asg_max_capacity"])
rsc_min_capacity = int(param_vals["Parameters"]["rsc_min_capacity"])
rsc_desired_capacity = int(param_vals["Parameters"]["rsc_desired_capacity"])
rsc_max_capacity = int(param_vals["Parameters"]["rsc_max_capacity"])
rsc_cont_mem_reserved = int(param_vals["Parameters"]["rsc_cont_mem_reserved"])
rspm_min_capacity = int(param_vals["Parameters"]["rspm_min_capacity"])
rspm_desired_capacity = int(param_vals["Parameters"]["rspm_desired_capacity"])
rspm_max_capacity = int(param_vals["Parameters"]["rspm_max_capacity"])
rspm_cont_mem_reserved = int(param_vals["Parameters"]["rspm_cont_mem_reserved"])
rsc_cookie_stickiness_duration = int(
    param_vals["Parameters"]["rsc_cookie_stickiness_duration"]
)
rsc_health_check_grace_period = int(
    param_vals["Parameters"]["rsc_health_check_grace_period"]
)
rspm_cookie_stickiness_duration = int(
    param_vals["Parameters"]["rspm_cookie_stickiness_duration"]
)
rspm_health_check_grace_period = int(
    param_vals["Parameters"]["rspm_health_check_grace_period"]
)
rsc_scale_in_cooldown = int(param_vals["Parameters"]["rsc_scale_in_cooldown"])
rsc_scale_out_cooldown = int(param_vals["Parameters"]["rsc_scale_out_cooldown"])
rsc_cpu_target_utilization_percent = int(
    param_vals["Parameters"]["rsc_cpu_target_utilization_percent"]
)
rsc_memory_target_utilization_percent = int(
    param_vals["Parameters"]["rsc_memory_target_utilization_percent"]
)
rsc_requests_per_target = int(param_vals["Parameters"]["rsc_requests_per_target"])
rspm_scale_in_cooldown = int(param_vals["Parameters"]["rspm_scale_in_cooldown"])
rspm_scale_out_cooldown = int(param_vals["Parameters"]["rspm_scale_out_cooldown"])
rspm_cpu_target_utilization_percent = int(
    param_vals["Parameters"]["rspm_cpu_target_utilization_percent"]
)
rspm_memory_target_utilization_percent = int(
    param_vals["Parameters"]["rspm_memory_target_utilization_percent"]
)
rspm_requests_per_target = int(param_vals["Parameters"]["rspm_requests_per_target"])


connect_pipeline_build = PipelineStack(
    app,
    id=f"RSCRSPM-{instance}",
    instance=instance,
    r53_base_domain=r53_base_domain,
    code_repo_name=code_repo_name,
    ec2_instance_type=ec2_instance_type,
    vpc_cidr=vpc_cidr,
    allowed_ips=allowed_ips,
    sns_email=sns_email,
    db_domain_suffix=db_domain_suffix,
    connect_cwlogs_key_alias=connect_cwlogs_key_alias,
    packagae_cwlogs_key_alias=packagae_cwlogs_key_alias,
    connect_efs_key_alias=connect_efs_key_alias,
    package_efs_key_alias=package_efs_key_alias,
    connect_db_key_alias=connect_db_key_alias,
    package_db_key_alias=package_db_key_alias,
    connect_repository_name=connect_repository_name,
    package_repository_name=package_repository_name,
    docker_secret_name=docker_secret_name,
    rsc_license_key_secret_name=rsc_license_key_secret_name,
    rspm_license_key_secret_name=rspm_license_key_secret_name,
    asg_min_capacity=asg_min_capacity,
    asg_desired_capacity=asg_desired_capacity,
    asg_max_capacity=asg_max_capacity,
    rsc_min_capacity=rsc_min_capacity,
    rsc_desired_capacity=rsc_desired_capacity,
    rsc_max_capacity=rsc_max_capacity,
    rsc_cont_mem_reserved=rsc_cont_mem_reserved,
    rspm_min_capacity=rspm_min_capacity,
    rspm_desired_capacity=rspm_desired_capacity,
    rspm_max_capacity=rspm_max_capacity,
    rspm_cont_mem_reserved=rspm_cont_mem_reserved,
    rsc_cookie_stickiness_duration=rsc_cookie_stickiness_duration,
    rsc_health_check_grace_period=rsc_health_check_grace_period,
    rspm_cookie_stickiness_duration=rspm_cookie_stickiness_duration,
    rspm_health_check_grace_period=rspm_health_check_grace_period,
    rsc_scale_in_cooldown=rsc_scale_in_cooldown,
    rsc_scale_out_cooldown=rsc_scale_out_cooldown,
    rsc_cpu_target_utilization_percent=rsc_cpu_target_utilization_percent,
    rsc_memory_target_utilization_percent=rsc_memory_target_utilization_percent,
    rsc_requests_per_target=rsc_requests_per_target,
    rspm_scale_in_cooldown=rspm_scale_in_cooldown,
    rspm_scale_out_cooldown=rspm_scale_out_cooldown,
    rspm_cpu_target_utilization_percent=rspm_cpu_target_utilization_percent,
    rspm_memory_target_utilization_percent=rspm_memory_target_utilization_percent,
    rspm_requests_per_target=rspm_requests_per_target,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
    ),
)

app.synth()
