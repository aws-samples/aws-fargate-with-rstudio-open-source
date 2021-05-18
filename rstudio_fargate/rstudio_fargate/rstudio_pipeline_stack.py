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

from aws_cdk.core import Stack, StackProps, Construct, SecretValue, RemovalPolicy
from aws_cdk import pipelines
from aws_cdk.pipelines import CdkPipeline, SimpleSynthAction
from .rstudio.rstudio_pipeline_stage import RstudioPipelineStage
from .rstudio.datasync_lambda.rstudio_pipeline_lambda_stage import RstudioPipelineLambdaStage
from .network.rstudio_network_account_stage import NetworkAccountStage
from .datalake.dl_resources_stage import DataLakeResourcesStage

import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_sns as sns
import aws_cdk.aws_sns_subscriptions as subscriptions
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as event_targets
import aws_cdk.aws_kms as kms
from aws_cdk import aws_iam as iam
from datetime import datetime, timezone

class RstudioPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        sns_email = self.node.try_get_context("sns_email_id")

        if sns_email is None:
            raise ValueError("Please provide email id for sending pipeline failure notifications")

        rstudio_code_repo_name = self.node.try_get_context("rstudio_code_repo_name")

        if rstudio_code_repo_name is None:
            raise ValueError("Please provide rstudio code repository name")

        network_account_id=self.node.try_get_context("network_account_id")
            
        if network_account_id is None:
            raise ValueError("Please provide account id of the network account")

        datalake_account_id=self.node.try_get_context("datalake_account_id")
            
        if datalake_account_id is None:
            raise ValueError("Please provide account id of the datalake account")
 
        instances = self.node.try_get_context("instances")

        if instances is None:
            raise ValueError("Please pass instance to use via context (dev/prod/...)")

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")

        rstudio_install_types = self.node.try_get_context("rstudio_install_types")

        if rstudio_install_types is None:
                raise ValueError("Please pass rstudio install type (ec2 or fargate)")

        rstudio_individual_containers = self.node.try_get_context("rstudio_individual_containers")

        if rstudio_individual_containers is None:
                raise ValueError("Please pass rstudio individual container required or not (true/false), false for ec2 install type")

        rstudio_container_memory_in_gb = self.node.try_get_context("rstudio_container_memory_in_gb")

        if rstudio_container_memory_in_gb is None:
                raise ValueError("Please pass rstudio container memory for your install type")

        shiny_container_memory_in_gb = self.node.try_get_context("shiny_container_memory_in_gb")

        if shiny_container_memory_in_gb is None:
                raise ValueError("Please pass shiny container memory for your instance")

        rstudio_ec2_instance_types = self.node.try_get_context("rstudio_ec2_instance_types")

        if rstudio_ec2_instance_types is None:
                raise ValueError("Please pass the ec2 instance type for your instance if your install type is ec2")
                
        rstudio_repo = codecommit.Repository.from_repository_arn(
            self,
            "Rstudio-repo",
            f"arn:aws:codecommit:{self.region}:{self.account}:{rstudio_code_repo_name}",
        )

        pipeline_name='RstudioDev'
        
        build_environment = codebuild.BuildEnvironment(
            build_image=codebuild.LinuxBuildImage.STANDARD_4_0,
            compute_type=codebuild.ComputeType.MEDIUM,
        )
        
        source_artifact = codepipeline.Artifact()

        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline_failure_topic_kms_key = kms.Key(
            self,
            'Rstudio-sns-key-',  
            alias= "alias/sns-rstudio-key",
            removal_policy=RemovalPolicy.DESTROY,
            enable_key_rotation= True,
            )

        pipeline_failure_topic_kms_key.add_to_resource_policy(
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
                    principals=[
                        iam.ServicePrincipal("sns.amazonaws.com")
                    ]
                )
            )

        pipeline_failure_topic = sns.Topic(
            self,
            'Rstudio-Pipeline-Failure-Topic-',
            display_name= f'Rstudio Pipeline On Fail Topic',
            master_key= pipeline_failure_topic_kms_key,
        )

        pipeline_failure_topic.add_subscription(subscriptions.EmailSubscription(sns_email))

        sns_event_target = event_targets.SnsTopic(
            pipeline_failure_topic,
            message=events.RuleTargetInput.from_text(
                "The pipeline {0} from account {1} has {2} at {3}.".format(
                    events.EventField.from_path(
                        "$.detail.pipeline"
                        ),  
                        events.EventField.account,
                        events.EventField.from_path("$.detail.state"),
                        events.EventField.time,
                    ),
                ),
            )

        rstudio_pipeline = pipelines.CdkPipeline(
            self, 
            "RstudioDev",
            pipeline_name=pipeline_name,
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="CodeCommit",
                output=source_artifact,
                repository=rstudio_repo),
            synth_action=SimpleSynthAction.standard_npm_synth(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                install_command="npm install -g aws-cdk@1.100.0 && pip install --upgrade pip && pip install -r requirements.txt && python -m pip install aws_cdk.aws_s3_deployment",
                synth_command="cdk synth",
                environment=build_environment,
                ),
            )

        rstudio_pipeline.code_pipeline.on_state_change(
            f'Rstudio-Pipeline-On-State-Change', 
            description='Send email when the rstudio pipeline fails',
            event_pattern=events.EventPattern(
                source= ['aws.codepipeline'],
                detail_type= ['CodePipeline Pipeline Execution State Change'],
                detail={
                    'state': ['FAILED'],
                    'pipeline': [rstudio_pipeline.code_pipeline.pipeline_name],
                }
            ),
            target= sns_event_target,
        )

        # Take the current pipeline_unique_id and use this to uniquely name some of the resources, such as IAM roles
        pipeline_unique_id = f'{pipeline_name}-{self.region}'
        
        rstudio_pipeline_lambda_stage=RstudioPipelineLambdaStage(
            self,
            "RstudioPipelineLambdaStage",
            pipeline_unique_id=pipeline_unique_id,
            env={
                "account":self.account,
                "region":self.region,
            }
        )
        
        rstudio_pipeline.add_application_stage(
            rstudio_pipeline_lambda_stage
        )
        
    
        datalake_resources_stage = DataLakeResourcesStage(
            self,
            "DataLakeResourcesStage",
            pipeline_unique_id=pipeline_unique_id,
            env={
                "account": datalake_account_id,
                "region":self.region,
            }
        )
        
        rstudio_deployment_stage = rstudio_pipeline.add_application_stage(
            datalake_resources_stage
        ) 
    
        network_account_stage = NetworkAccountStage(
            self,
            "NetworkAccountStage",
            pipeline_unique_id=pipeline_unique_id,
            env={
                "account": network_account_id,
                "region":self.region,
            }
        )
        rstudio_deployment_stage = rstudio_pipeline.add_application_stage(
            network_account_stage
        ) 
        
        instances=instances.split(",")
        rstudio_account_ids=rstudio_account_ids.split(",")
        rstudio_install_types=rstudio_install_types.split(",")
        rstudio_individual_containers=rstudio_individual_containers.split(",")
        rstudio_container_memory_in_gb=rstudio_container_memory_in_gb.split(",")
        shiny_container_memory_in_gb=shiny_container_memory_in_gb.split(",")
        rstudio_ec2_instance_types=rstudio_ec2_instance_types.split(",")
        
        rstudio_stage_instances = []
        rstudio_stage_account_ids = []
        rstudio_stage_install_types = []
        rstudio_stage_individual_containers = []
        rstudio_stage_container_memory_in_gb = []
        shiny_stage_container_memory_in_gb = []
        rstudio_stage_ec2_instance_types = []
        
        stage_count = 0
    
        for i in range(len(instances)):
            instance=instances[i]
            rstudio_account_id=rstudio_account_ids[i]
            rstudio_install_type=rstudio_install_types[i]
            rstudio_individual_container=rstudio_individual_containers[i]
            rstudio_container_memory=rstudio_container_memory_in_gb[i]
            shiny_container_memory=shiny_container_memory_in_gb[i]
            rstudio_ec2_instance_type=rstudio_ec2_instance_types[i]
            
            # Append variables to the lists
            rstudio_stage_instances.append(instance)
            rstudio_stage_account_ids.append(rstudio_account_id)
            rstudio_stage_install_types.append(rstudio_install_type)
            rstudio_stage_individual_containers.append(rstudio_individual_container)
            rstudio_stage_container_memory_in_gb.append(rstudio_container_memory)
            shiny_stage_container_memory_in_gb.append(shiny_container_memory)
            rstudio_stage_ec2_instance_types.append(rstudio_ec2_instance_type)
            
            if(len(rstudio_stage_account_ids) == 2): # We can only handle a maximum of 2 instances per stage
                self.create_stage(rstudio_pipeline, self.account, self.region, stage_count, rstudio_stage_instances,
                    rstudio_stage_account_ids,
                    rstudio_stage_install_types,
                    rstudio_stage_individual_containers,
                    rstudio_stage_container_memory_in_gb,
                    shiny_stage_container_memory_in_gb,
                    rstudio_stage_ec2_instance_types,
                    pipeline_unique_id)
                
                # Clear previous values
                rstudio_stage_instances.clear()
                rstudio_stage_account_ids.clear()
                rstudio_stage_install_types.clear()
                rstudio_stage_individual_containers.clear()
                rstudio_stage_container_memory_in_gb.clear()
                shiny_stage_container_memory_in_gb.clear()
                rstudio_stage_ec2_instance_types.clear()
        
                stage_count = stage_count+1 # Increment the number of stages we have so far.
        
        #Process any remaing instance accounts here
        if(len(rstudio_stage_account_ids) > 0):
            self.create_stage(rstudio_pipeline, self.account, self.region, stage_count, rstudio_stage_instances,
                    rstudio_stage_account_ids,
                    rstudio_stage_install_types,
                    rstudio_stage_individual_containers,
                    rstudio_stage_container_memory_in_gb,
                    shiny_stage_container_memory_in_gb,
                    rstudio_stage_ec2_instance_types,
                    pipeline_unique_id)        
            
    def create_stage(self, rstudio_pipeline, account, region, stage_count, rstudio_stage_instances,
        rstudio_stage_account_ids,
        rstudio_stage_install_types,
        rstudio_stage_individual_containers,
        rstudio_stage_container_memory_in_gb,
        shiny_stage_container_memory_in_gb,
        rstudio_stage_ec2_instance_types,
        pipeline_unique_id):
            
        print(f'Creating a new Rstudio stage for instances {str(rstudio_stage_instances)}')
        
        rstudio_stage = RstudioPipelineStage(
                    self,
                    f"RstudioStage-{stage_count}",
                    instances=rstudio_stage_instances,
                    rstudio_account_ids=rstudio_stage_account_ids,
                    rstudio_install_types=rstudio_stage_install_types,
                    rstudio_individual_containers=rstudio_stage_individual_containers,
                    rstudio_container_memory_in_gb=rstudio_stage_container_memory_in_gb,
                    shiny_container_memory_in_gb=shiny_stage_container_memory_in_gb,
                    rstudio_ec2_instance_types=rstudio_stage_ec2_instance_types,
                    pipeline_unique_id=pipeline_unique_id,
                    env={
                        "account": self.account,
                        "region": self.region,
                    }
                )
                
        rstudio_pipeline.add_application_stage(
            rstudio_stage
        )
            
        print(f'Number of actions in new rstudio stage {len(rstudio_stage.node.children)}')
        