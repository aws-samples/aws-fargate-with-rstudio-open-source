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

from aws_cdk import core as cdk
from rstudio_fargate.rstudio_pipeline_stack import RstudioPipelineStack

from rstudio_configuration_stack import RstudioConfigurationStack

app = cdk.App()

ses_email_verification_check = app.node.try_get_context("ses_email_verification_check")

if ses_email_verification_check is None:
    raise ValueError("Please run check_ses_email.sh and ensure all emails are verified.")
else:
    if not ses_email_verification_check:
        raise ValueError("Please run check_ses_email.sh and ensure all emails are verified.")

instances = app.node.try_get_context("instances")

if instances is None:
    raise ValueError("Please pass instances to use via context (dev/prod/...)")

rstudio_account_ids = app.node.try_get_context("rstudio_account_ids")

if rstudio_account_ids is None:
    raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")

rstudio_users = app.node.try_get_context("rstudio_users")

if rstudio_users is None:
    raise ValueError("Please provide comma-separated list of rstudio frontend users")

rstudio_ec2_instance_types = app.node.try_get_context("rstudio_ec2_instance_types")

if rstudio_ec2_instance_types is None:
    raise ValueError("Please provide ec2 instance type for ECS cluster")

rstudio_individual_containers = app.node.try_get_context("rstudio_individual_containers")

if rstudio_individual_containers is None:
    raise ValueError("Please provide parameter for rstudio individual containers true/false")

rstudio_container_memory_in_gb = app.node.try_get_context("rstudio_container_memory_in_gb")

if rstudio_container_memory_in_gb is None:
    raise ValueError("Please pass rstudio container memory for your install type")

shiny_container_memory_in_gb = app.node.try_get_context("shiny_container_memory_in_gb")

if shiny_container_memory_in_gb is None:
    raise ValueError("Please pass shiny container memory for your instance")

number_of_shiny_containers = app.node.try_get_context("number_of_shiny_containers")

if number_of_shiny_containers is None:
    raise ValueError("Please provide number of shiny containers to deploy")

rstudio_ec2_instance_types = app.node.try_get_context("rstudio_ec2_instance_types")

if rstudio_ec2_instance_types is None:
    raise ValueError("Please pass the ec2 instance type for your instance if your install type is ec2")

rstudio_pipeline_account_id = app.node.try_get_context("rstudio_pipeline_account_id")

if rstudio_pipeline_account_id is None:
    raise ValueError("Please supply the central development account id")

rstudio_code_repo_name = app.node.try_get_context("rstudio_code_repo_name")

if rstudio_code_repo_name is None:
    raise ValueError("Please provide rstudio code repository name")

rstudio_image_repo_name = app.node.try_get_context("rstudio_image_repo_name")

if rstudio_image_repo_name is None:
    raise ValueError("Please provide rstudio docker image ecr repository name")

shiny_image_repo_name = app.node.try_get_context("shiny_image_repo_name")

if shiny_image_repo_name is None:
    raise ValueError("Please provide shiny docker image ecr repository name")

ssh_image_repo_name = app.node.try_get_context("ssh_image_repo_name")

if ssh_image_repo_name is None:
    raise ValueError("Please provide ssh server docker image ecr repository name")

r53_base_domain = app.node.try_get_context("r53_base_domain")

if r53_base_domain is None:
    raise ValueError("Please provide base route 53 domain for the build")

r53_sub_domain = app.node.try_get_context("r53_sub_domain")

if r53_sub_domain is None:
    raise ValueError("Please provide base route 53 subdomain for the build")
          
vpc_cidr = app.node.try_get_context("vpc_cidr_range")

if vpc_cidr is None:
    raise ValueError("Please provide vpc cidr range for the build")

bastion_client_ip = app.node.try_get_context("bastion_client_ip_range")

if bastion_client_ip is None:
    raise ValueError("Please provide client ip range allowed to access bastion fargate ssh server")
        
encryption_key_arn = app.node.try_get_context("encryption_key_arn")

if encryption_key_arn is None:
    raise ValueError("Please provide encryption key arn")

allowed_ips = app.node.try_get_context("allowed_ips")

if allowed_ips is None:
    print("List of allowed IP addresses is not provided, will default to ALLOW all IPs through the WAf for rstudio/shiny")

sns_email = app.node.try_get_context("sns_email_id")

if sns_email is None:
    raise ValueError("Please provide email id for sending pipeline failure notifications")

network_account_id = app.node.try_get_context("network_account_id")

if network_account_id is None:
    raise ValueError("Please supply the central network account id")

datalake_account_id = app.node.try_get_context("datalake_account_id")

if datalake_account_id is None:
    raise ValueError("Please supply the central data account id")
                
datalake_aws_region = app.node.try_get_context("datalake_aws_region")

if datalake_aws_region is None:
    raise ValueError("Please provide datalake account region")

datalake_source_bucket_name = app.node.try_get_context("datalake_source_bucket_name")

if datalake_source_bucket_name is None:
    raise ValueError("Please supply prefix for the data upload bucket")

rstudio_athena_bucket_name=app.node.try_get_context("rstudio_athena_bucket_name")
            
if rstudio_athena_bucket_name is None:
    raise ValueError("Please provide name for rstudio Athena bucket")

rstudio_athena_wg_name=app.node.try_get_context("rstudio_athena_bucket_name")
            
if rstudio_athena_wg_name is None:
    raise ValueError("Please provide name for rstudio Athena workgroup")
      
datalake_source_bucket_key_hourly = app.node.try_get_context("datalake_source_bucket_key_hourly")

if datalake_source_bucket_key_hourly is None:
    raise ValueError("Please supply the name of the folder to use for hourly uploads in the datalake bucket")  
    
datalake_source_bucket_key_instant = app.node.try_get_context("datalake_source_bucket_key_instant")

if datalake_source_bucket_key_instant is None:
    raise ValueError("Please supply the name of the folder to use for instant uploads in the datalake bucket")

rstudio_pipeline_build = RstudioPipelineStack(
    app, 
    "Rstudio-Piplenine-Stack",
    env= cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
        )
    )

rstudio_configuration_build = RstudioConfigurationStack(
    app, 
    "Rstudio-Configuration-Stack",
    env= cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
        )
    )
    
app.synth()
