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

from .rstudio.rstudio_pipeline_stage import PipelineStage
from .datasync_trigger.datasync_trigger_lambda_stage import DataSyncTriggerLambdaStage
from .network.rstudio_network_account_stage import NetworkAccountStage
from .datalake.dl_resources_stage import DataLakeResourcesStage

from aws_cdk import (
    core as cdk,
    pipelines,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_events as events,
    aws_events_targets as event_targets,
    aws_kms as kms,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_ecr as ecr,
    aws_secretsmanager as sm,
)
from aws_cdk.core import (
    Stack,
    StackProps,
    Construct,
    SecretValue,
    RemovalPolicy,
)
from aws_cdk.pipelines import (
    CdkPipeline,
    SimpleSynthAction,
)


class RstudioPipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        instance: str,
        rstudio_account_id: str,
        rstudio_pipeline_account_id: str,
        network_account_id: str,
        datalake_account_id: str,
        datalake_aws_region: str,
        code_repo_name: str,
        r53_base_domain: str,
        rstudio_install_type: str,
        rstudio_ec2_instance_type: str,
        rstudio_container_memory_in_gb: str,
        number_of_rstudio_containers: int,
        vpc_cidr_range: str,
        allowed_ips: str,
        sns_email: str,
        datalake_source_bucket_name: str,
        athena_output_bucket_name: str,
        athena_workgroup_name: str,
        lambda_datasync_trigger_function_arn: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        datasync_task_arn_ssm_param_name: str,
        datasync_function_name: str,
        rstudio_container_repository_name: str,
        shiny_container_repository_name: str,
        rstudio_container_repository_name_ssm_param: str,
        rstudio_container_repository_arn_ssm_param: str,
        shiny_container_repository_name_ssm_param: str,
        shiny_container_repository_arn_ssm_param: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        ecs_cluster_name: str,
        rstudio_cwlogs_key_alias: str,
        shiny_cwlogs_key_alias: str,
        rstudio_efs_key_alias: str,
        shiny_efs_key_alias: str,
        rstudio_user_key_alias: str,
        docker_secret_name: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        shiny_min_capacity: int,
        shiny_desired_capacity: int,
        shiny_max_capacity: int,
        shiny_container_memory_in_gb: int,
        rstudio_container_memory_reserved: int,
        rstudio_health_check_grace_period: int,
        shiny_health_check_grace_period: int,
        shiny_cookie_stickiness_duration: int,
        shiny_scale_in_cooldown: int,
        shiny_scale_out_cooldown: int,
        shiny_cpu_target_utilization_percent: int,
        shiny_memory_target_utilization_percent: int,
        shiny_requests_per_target: int,
        datalake_source_bucket_key_hourly: str,
        access_point_path_hourly: str,
        datalake_source_bucket_key_instant: str,
        access_point_path_instant: str,
        athena_output_bucket_key: str,
        s3_lifecycle_expiration_duration: int,
        s3_trasnition_duration_infrequent_access: int,
        s3_trasnition_duration_glacier: int,
        home_container_path: str,
        shiny_share_container_path: str,
        hourly_sync_container_path: str,
        instant_sync_container_path: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        rstudio_repo = codecommit.Repository.from_repository_arn(
            self,
            id=f"Rstudio-Shiny-repo-{instance}",
            repository_arn=f"arn:aws:codecommit:{self.region}:{self.account}:{code_repo_name}",
        )

        role_principals = []

        role_principals.append(iam.AccountPrincipal(rstudio_account_id))

        role_principals.append(
            iam.ArnPrincipal(
                f"arn:aws:iam::{rstudio_account_id}:role/cdk-hnb659fds-image-publishing-role-{rstudio_account_id}-{self.region}"
            )
        )

        ecr_statement = iam.PolicyStatement(
            actions=[
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer",
            ],
            effect=iam.Effect.ALLOW,
            principals=role_principals,
        )

        # ECR repositories
        rstudio_container_repository = ecr.Repository(
            scope=self,
            id=f"{code_repo_name}-rstudio-container-{instance}",
            repository_name=rstudio_container_repository_name,
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        rstudio_container_repository.add_to_resource_policy(statement=ecr_statement)

        shiny_container_repository = ecr.Repository(
            scope=self,
            id=f"{code_repo_name}-shiny-container-{instance}",
            repository_name=shiny_container_repository_name,
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        shiny_container_repository.add_to_resource_policy(statement=ecr_statement)

        buildspec_docker = codebuild.BuildSpec.from_source_filename("buildspec.yml")

        dockerid = sm.Secret.from_secret_name_v2(
            self, id=f"ImportedDockerId-{instance}", secret_name=docker_secret_name
        )

        build_environment = codebuild.BuildEnvironment(
            build_image=codebuild.LinuxBuildImage.STANDARD_4_0,
            compute_type=codebuild.ComputeType.MEDIUM,
            privileged=True,
        )

        docker_build = codebuild.PipelineProject(
            scope=self,
            id=f"DockerBuild-{instance}",
            environment=build_environment,
            environment_variables={
                "RSTUDIO_REPO_ECR": codebuild.BuildEnvironmentVariable(
                    value=rstudio_container_repository.repository_uri
                ),
                "SHINY_REPO_ECR": codebuild.BuildEnvironmentVariable(
                    value=shiny_container_repository.repository_uri
                ),
                "DOCKER_HUB_USERNAME": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f"{dockerid.secret_name}:username",
                ),
                "DOCKER_HUB_PASSWORD": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f"{dockerid.secret_name}:password",
                ),
                "AWS_DEFAULT_ACCOUNT": codebuild.BuildEnvironmentVariable(
                    value=self.account
                ),
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(
                    value=self.region
                ),
            },
            build_spec=buildspec_docker,
        )

        rstudio_container_repository.grant_pull_push(docker_build)
        shiny_container_repository.grant_pull_push(docker_build)
        dockerid.grant_read(docker_build)

        docker_build.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                ],
                resources=[
                    f"arn:{cdk.Stack.of(self).partition}:ecr:{cdk.Stack.of(self).region}:{cdk.Stack.of(self).account}:repository/{rstudio_container_repository_name}",
                    f"arn:{cdk.Stack.of(self).partition}:ecr:{cdk.Stack.of(self).region}:{cdk.Stack.of(self).account}:repository/{shiny_container_repository_name}",
                ],
            )
        )

        source_artifact = codepipeline.Artifact()
        docker_output = codepipeline.Artifact(artifact_name="Docker")
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline_failure_topic_kms_key = kms.Key(
            self,
            id=f"Rstudio-sns-key-{instance}",
            alias=f"alias/sns-rstudio-key-{instance}",
            removal_policy=RemovalPolicy.DESTROY,
            enable_key_rotation=True,
        )

        pipeline_failure_topic_kms_key.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:kms:{self.region}:{self.account}:alias/sns-rstudio-key-{instance}"
                ],
                principals=[iam.ServicePrincipal("sns.amazonaws.com")],
            )
        )

        pipeline_failure_topic = sns.Topic(
            self,
            id=f"Rstudio-Pipeline-Failure-Topic-{instance}",
            display_name=f"Rstudio Pipeline On Fail Topic",
            master_key=pipeline_failure_topic_kms_key,
        )

        pipeline_failure_topic.add_subscription(
            subscriptions.EmailSubscription(sns_email)
        )

        sns_event_target = event_targets.SnsTopic(
            pipeline_failure_topic,
            message=events.RuleTargetInput.from_text(
                "The pipeline {0} from account {1} has {2} at {3}.".format(
                    events.EventField.from_path("$.detail.pipeline"),
                    events.EventField.account,
                    events.EventField.from_path("$.detail.state"),
                    events.EventField.time,
                ),
            ),
        )

        pipeline_name = f"Rstudio-Shiny-{instance}"

        rstudio_pipeline = pipelines.CdkPipeline(
            self,
            id=f"RstudioPipeline-{instance}",
            pipeline_name=pipeline_name,
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="CodeCommit",
                output=source_artifact,
                repository=rstudio_repo,
            ),
            synth_action=SimpleSynthAction.standard_npm_synth(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                install_command="npm install -g aws-cdk && pip install --upgrade pip && pip install -r requirements.txt && python -m pip install aws_cdk.aws_s3_deployment",
                synth_command="cdk synth",
                environment=build_environment,
            ),
        )

        rstudio_pipeline.code_pipeline.on_state_change(
            f"Rstudio-Pipeline-On-State-Change-{instance}",
            description="Send email when the rstudio pipeline fails",
            event_pattern=events.EventPattern(
                source=["aws.codepipeline"],
                detail_type=["CodePipeline Pipeline Execution State Change"],
                detail={
                    "state": ["FAILED"],
                    "pipeline": [rstudio_pipeline.code_pipeline.pipeline_name],
                },
            ),
            target=sns_event_target,
        )

        # Take the current pipeline_unique_id and use this to uniquely name some of the resources, such as IAM roles
        pipeline_unique_id = f"{pipeline_name}-{self.region}"

        rstudio_container_repository_name = ssm.StringParameter(
            self,
            id=f"rstudio-repo-name-{instance}",
            description="SSM parameter to save rstudio ecr repo name",
            parameter_name=rstudio_container_repository_name_ssm_param,
            string_value=rstudio_container_repository.repository_name,
            tier=ssm.ParameterTier.ADVANCED,
        )

        rstudio_container_repository_arn = ssm.StringParameter(
            self,
            id=f"rstudio-repo-arn-{instance}",
            description="SSM parameter to save rstudio ecr repo arn",
            parameter_name=rstudio_container_repository_arn_ssm_param,
            string_value=rstudio_container_repository.repository_arn,
            tier=ssm.ParameterTier.ADVANCED,
        )

        shiny_container_repository_name = ssm.StringParameter(
            self,
            id=f"shiny-repo-name-{instance}",
            description="SSM parameter to save shiny ecr repo name",
            parameter_name=shiny_container_repository_name_ssm_param,
            string_value=shiny_container_repository.repository_name,
            tier=ssm.ParameterTier.ADVANCED,
        )

        shiny_container_repository_arn = ssm.StringParameter(
            self,
            id=f"shiny-repo-arn-{instance}",
            description="SSM parameter to save shiny ecr repo arn",
            parameter_name=shiny_container_repository_arn_ssm_param,
            string_value=shiny_container_repository.repository_arn,
            tier=ssm.ParameterTier.ADVANCED,
        )

        ssm_policy = iam.ManagedPolicy(
            self,
            id=f"SSM-Cross-Account-Policy-{instance}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:DescribeParameters",
                    ],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter{rstudio_container_repository_name_ssm_param}",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter{rstudio_container_repository_arn_ssm_param}",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter{shiny_container_repository_name_ssm_param}",
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter{shiny_container_repository_arn_ssm_param}",
                    ],
                ),
            ],
        )

        principal = []

        principal.append(iam.AccountPrincipal(rstudio_account_id))

        composite_principal = iam.CompositePrincipal(*principal)

        ssm_cross_account_role = iam.Role(
            self,
            id=f"SSM-Cross-Account-Role-{instance}",
            role_name=ssm_cross_account_role_name,
            assumed_by=composite_principal,
        )

        ssm_policy.attach_to_role(ssm_cross_account_role)

        rstudio_container_repository_name.grant_read(ssm_cross_account_role)
        rstudio_container_repository_arn.grant_read(ssm_cross_account_role)
        shiny_container_repository_name.grant_read(ssm_cross_account_role)
        shiny_container_repository_arn.grant_read(ssm_cross_account_role)

        docker_build = rstudio_pipeline.code_pipeline.add_stage(
            stage_name="DockerBuild",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name=f"DockerBuild_and_Push_ECR",
                    project=docker_build,
                    input=source_artifact,
                    outputs=[docker_output],
                )
            ],
        )

        rstudio_datasync_trigger_stage = DataSyncTriggerLambdaStage(
            self,
            id=f"DataSyncTrigger",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            datalake_account_id=datalake_account_id,
            datalake_source_bucket_name=datalake_source_bucket_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            datasync_task_arn_ssm_param_name=datasync_task_arn_ssm_param_name,
            datasync_function_name=datasync_function_name,
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        rstudio_pipeline.add_application_stage(rstudio_datasync_trigger_stage)

        datalake_resources_stage = DataLakeResourcesStage(
            self,
            id=f"RstudioDataLake",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            datalake_source_bucket_name=datalake_source_bucket_name,
            datalake_source_bucket_key_hourly=datalake_source_bucket_key_hourly,
            datalake_source_bucket_key_instant=datalake_source_bucket_key_instant,
            lambda_datasync_trigger_function_arn=lambda_datasync_trigger_function_arn,
            athena_output_bucket_name=athena_output_bucket_name,
            athena_workgroup_name=athena_workgroup_name,
            athena_output_bucket_key=athena_output_bucket_key,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            s3_lifecycle_expiration_duration=s3_lifecycle_expiration_duration,
            s3_trasnition_duration_infrequent_access=s3_trasnition_duration_infrequent_access,
            s3_trasnition_duration_glacier=s3_trasnition_duration_glacier,
            env={
                "account": datalake_account_id,
                "region": self.region,
            },
        )

        rstudio_deployment_stage = rstudio_pipeline.add_application_stage(
            datalake_resources_stage
        )

        network_account_stage = NetworkAccountStage(
            self,
            id="RstudioNetwork",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            r53_base_domain=r53_base_domain,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            env={
                "account": network_account_id,
                "region": self.region,
            },
        )
        rstudio_deployment_stage = rstudio_pipeline.add_application_stage(
            network_account_stage
        )

        rstudio_stage = PipelineStage(
            self,
            id=f"RstudioShinyApp",
            instance=instance,
            rstudio_account_id=rstudio_account_id,
            network_account_id=network_account_id,
            datalake_account_id=datalake_account_id,
            rstudio_install_type=rstudio_install_type,
            rstudio_ec2_instance_type=rstudio_ec2_instance_type,
            rstudio_container_memory_in_gb=rstudio_container_memory_in_gb,
            number_of_rstudio_containers=number_of_rstudio_containers,
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
            home_container_path=home_container_path,
            shiny_share_container_path=shiny_share_container_path,
            hourly_sync_container_path=hourly_sync_container_path,
            instant_sync_container_path=instant_sync_container_path,
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        rstudio_pipeline.add_application_stage(rstudio_stage)
