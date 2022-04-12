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

from .route53.pipeline_stage import PipelineStage
from .network.network_account_stage import NetworkAccountStage

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


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        instance: str,
        app_account_id: str,
        network_account_id: str,
        code_repo_name: str,
        r53_base_domain: str,
        r53_sub_domain: str,
        ssm_cross_account_role_name: str,
        ssm_cross_account_lambda_role_name: str,
        ssm_route53_delegation_name: str,
        ssm_route53_delegation_id: str,
        r53_delegation_role_name: str,
        sns_email: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        app_repo = codecommit.Repository.from_repository_arn(
            self,
            id=f"app-repo-{instance}",
            repository_arn=f"arn:aws:codecommit:{self.region}:{self.account}:{code_repo_name}",
        )

        pipeline_failure_topic_kms_key = kms.Key(
            self,
            id=f"r53-zone-delegation-pipeline-sns-key-{instance}",
            alias=f"alias/sns-r53-zone-delegation-pipeline-key-{instance}",
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
                    f"arn:aws:kms:{self.region}:{self.account}:alias/sns-r53-zone-delegation-pipeline-key-{instance}"
                ],
                principals=[iam.ServicePrincipal("sns.amazonaws.com")],
            )
        )

        pipeline_failure_topic = sns.Topic(
            self,
            id=f"App-Pipeline-Failure-Topic-{instance}",
            display_name=f"R53 Zone Delegation Pipeline On Fail Topic",
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

        build_environment = codebuild.BuildEnvironment(
            build_image=codebuild.LinuxBuildImage.STANDARD_4_0,
            compute_type=codebuild.ComputeType.MEDIUM,
            privileged=True,
        )
        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline_name = f"R53-Zone-Delegation-{instance}"

        r53_pipeline = pipelines.CdkPipeline(
            self,
            id=f"r53-zone-delegation-pipeline-{instance}",
            pipeline_name=pipeline_name,
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="CodeCommit",
                output=source_artifact,
                repository=app_repo,
            ),
            synth_action=SimpleSynthAction.standard_npm_synth(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                install_command="npm install -g aws-cdk && pip install --upgrade pip && pip install -r requirements.txt",
                synth_command="cdk synth",
                environment=build_environment,
            ),
        )

        r53_pipeline.code_pipeline.on_state_change(
            f"r53-Zone-Delegation-Pipeline-On-State-Change-{instance}",
            description="Send email when the r53 zone delegation pipeline fails",
            event_pattern=events.EventPattern(
                source=["aws.codepipeline"],
                detail_type=["CodePipeline Pipeline Execution State Change"],
                detail={
                    "state": ["FAILED"],
                    "pipeline": [r53_pipeline.code_pipeline.pipeline_name],
                },
            ),
            target=sns_event_target,
        )

        network_account_stage = NetworkAccountStage(
            self,
            id="R53Network",
            instance=instance,
            app_account_id=app_account_id,
            r53_base_domain=r53_base_domain,
            r53_sub_domain=r53_sub_domain,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            env={
                "account": network_account_id,
                "region": self.region,
            },
        )
        r53_deployment_stage = r53_pipeline.add_application_stage(
            network_account_stage
        )

        app_stage = PipelineStage(
            self,
            id=f"AppStage",
            instance=instance,
            app_account_id=app_account_id,
            network_account_id=network_account_id,
            ssm_cross_account_role_name=ssm_cross_account_role_name,
            ssm_cross_account_lambda_role_name=ssm_cross_account_lambda_role_name,
            ssm_route53_delegation_name=ssm_route53_delegation_name,
            ssm_route53_delegation_id=ssm_route53_delegation_id,
            r53_delegation_role_name=r53_delegation_role_name,
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        r53_pipeline.add_application_stage(app_stage)
