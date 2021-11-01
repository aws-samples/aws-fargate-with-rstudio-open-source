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

from .pipeline_stage import PipelineStage

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
    aws_ecr as ecr,
    aws_secretsmanager as sm,
)
from aws_cdk.core import (
    Stack,
    StackProps,
    Construct,
    SecretValue,
    RemovalPolicy,
    CfnOutput,
)
from aws_cdk.pipelines import (
    CdkPipeline,
    SimpleSynthAction,
)


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        instance: str,
        r53_base_domain: str,
        code_repo_name: str,
        ec2_instance_type: str,
        vpc_cidr: str,
        allowed_ips: str,
        sns_email: str,
        db_domain_suffix: str,
        connect_cwlogs_key_alias: str,
        packagae_cwlogs_key_alias: str,
        connect_efs_key_alias: str,
        package_efs_key_alias: str,
        connect_db_key_alias: str,
        package_db_key_alias: str,
        connect_repository_name: str,
        package_repository_name: str,
        docker_secret_name: str,
        rsc_license_key_secret_name: str,
        rspm_license_key_secret_name: str,
        asg_min_capacity: int,
        asg_desired_capacity: int,
        asg_max_capacity: int,
        rsc_min_capacity: int,
        rsc_desired_capacity: int,
        rsc_max_capacity: int,
        rsc_cont_mem_reserved: int,
        rspm_min_capacity: int,
        rspm_desired_capacity: int,
        rspm_max_capacity: int,
        rspm_cont_mem_reserved: int,
        rsc_cookie_stickiness_duration: int,
        rsc_health_check_grace_period: int,
        rspm_cookie_stickiness_duration: int,
        rspm_health_check_grace_period: int,
        rsc_scale_in_cooldown: int,
        rsc_scale_out_cooldown: int,
        rsc_cpu_target_utilization_percent: int,
        rsc_memory_target_utilization_percent: int,
        rsc_requests_per_target: int,
        rspm_scale_in_cooldown: int,
        rspm_scale_out_cooldown: int,
        rspm_cpu_target_utilization_percent: int,
        rspm_memory_target_utilization_percent: int,
        rspm_requests_per_target: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        code_repo = codecommit.Repository.from_repository_arn(
            self,
            f"RSC-RSPM-code-repo-{instance}",
            f"arn:aws:codecommit:{self.region}:{self.account}:{code_repo_name}",
        )

        role_principal = []

        role_principal.append(iam.AccountPrincipal(self.account))

        ecr_statement = iam.PolicyStatement(
            actions=[
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
                "ecr:CompleteLayerUpload",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart",
            ],
            effect=iam.Effect.ALLOW,
            principals=role_principal,
        )

        # ECR repositories
        connect_container_repository = ecr.Repository(
            scope=self,
            id=f"{code_repo_name}-connect-container-{instance}",
            repository_name=connect_repository_name,
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        connect_container_repository.add_to_resource_policy(statement=ecr_statement)

        package_container_repository = ecr.Repository(
            scope=self,
            id=f"{code_repo_name}-package-container-{instance}",
            repository_name=package_repository_name,
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        package_container_repository.add_to_resource_policy(statement=ecr_statement)

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
            id=f"DockerBuild",
            environment=build_environment,
            environment_variables={
                "CONNECT_REPO_ECR": codebuild.BuildEnvironmentVariable(
                    value=connect_container_repository.repository_uri
                ),
                "PACKAGE_REPO_ECR": codebuild.BuildEnvironmentVariable(
                    value=package_container_repository.repository_uri
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

        connect_container_repository.grant_pull_push(docker_build)
        package_container_repository.grant_pull_push(docker_build)
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
                    f"arn:{cdk.Stack.of(self).partition}:ecr:{cdk.Stack.of(self).region}:{cdk.Stack.of(self).account}:repository/{connect_repository_name}",
                    f"arn:{cdk.Stack.of(self).partition}:ecr:{cdk.Stack.of(self).region}:{cdk.Stack.of(self).account}:repository/{package_repository_name}",
                ],
            )
        )

        source_artifact = codepipeline.Artifact()
        docker_output = codepipeline.Artifact(artifact_name="Docker")
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline_failure_topic_kms_key = kms.Key(
            self,
            id=f"RSCRSPM-sns-key-{instance}",
            alias=f"alias/sns-connect-key-{instance}",
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
                    f"arn:aws:kms:{self.region}:{self.account}:alias/sns-connect-key-{instance}"
                ],
                principals=[iam.ServicePrincipal("sns.amazonaws.com")],
            )
        )

        pipeline_failure_topic = sns.Topic(
            self,
            id=f"RSCRSPM-Pipeline-Failure-Topic-{instance}",
            display_name=f"connect {instance} Pipeline On Fail Topic",
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

        app_pipeline = pipelines.CdkPipeline(
            self,
            id=f"RSCRSPM-Pipeline-{instance}",
            pipeline_name=f"RSC-RSPM-App-Pipeline-{instance}",
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="CodeCommit", output=source_artifact, repository=code_repo
            ),
            synth_action=SimpleSynthAction.standard_npm_synth(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                install_command="npm install -g aws-cdk && pip install --upgrade pip && pip install -r requirements.txt",
                synth_command="cdk synth",
                environment=build_environment,
            ),
        )

        app_pipeline.code_pipeline.on_state_change(
            f"RSCRSPM-{instance}-Pipeline-On-State-Change",
            description="Send email when the pipeline fails",
            event_pattern=events.EventPattern(
                source=["aws.codepipeline"],
                detail_type=["CodePipeline Pipeline Execution State Change"],
                detail={
                    "state": ["FAILED"],
                    "pipeline": [app_pipeline.code_pipeline.pipeline_name],
                },
            ),
            target=sns_event_target,
        )

        docker_build = app_pipeline.code_pipeline.add_stage(
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

        app_stage = PipelineStage(
            self,
            id="RSCRSPMStage",
            instance=instance,
            r53_base_domain=r53_base_domain,
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
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        app_deployment_stage = app_pipeline.add_application_stage(app_stage)

        # Pass stack variables to other stacks

        CfnOutput(
            self,
            f"Connect-ECR-Repo-Name-{instance}",
            export_name=f"Connect-ECR-Repo-Name-{instance}",
            value=connect_container_repository.repository_name,
        )

        CfnOutput(
            self,
            f"Connect-ECR-Repo-Arn-{instance}",
            export_name=f"Connect-ECR-Repo-Arn-{instance}",
            value=connect_container_repository.repository_arn,
        )

        CfnOutput(
            self,
            f"Package-ECR-Repo-Name-{instance}",
            export_name=f"Package-ECR-Repo-Name-{instance}",
            value=package_container_repository.repository_name,
        )

        CfnOutput(
            self,
            f"Package-ECR-Repo-Arn-{instance}",
            export_name=f"Package-ECR-Repo-Arn-{instance}",
            value=package_container_repository.repository_arn,
        )
