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

from aws_cdk import (
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ecr as ecr,
    aws_iam as iam,
    core as cdk,
    aws_secretsmanager as sm
)    
from aws_cdk.core import RemovalPolicy


class DockerPipelineStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        rstudio_account_ids = self.node.try_get_context("rstudio_account_ids")

        if rstudio_account_ids is None:
            raise ValueError("Please supply the comma separated aws account ids of the rstudio accounts")
            
        name = scope.node.try_get_context("name")

        codecommit_repo = codecommit.Repository.from_repository_arn(
            self,
            "Rstudio-repo",
            f"arn:aws:codecommit:{self.region}:{self.account}:{name}",
        )

        role_principals = []
        
        for account in rstudio_account_ids.split(","):
            role_principals.append(
                iam.AccountPrincipal(account)
            )

            role_principals.append(
                iam.ArnPrincipal(f'arn:aws:iam::{account}:role/cdk-hnb659fds-image-publishing-role-{account}-{self.region}')
            )            
            
        our_statement=iam.PolicyStatement(
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer"
                        ],
                        effect=iam.Effect.ALLOW,
                        principals=role_principals
                    )
                    
        # ECR repositories
        rstudio_container_repository = ecr.Repository(
            scope=self,
            id=f"{name}-rstudio-container",
            repository_name=f"{name}_rstudio_image",
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        rstudio_container_repository.add_to_resource_policy(
            statement=our_statement
        )
        
        openssh_container_repository = ecr.Repository(
            scope=self,
            id=f"{name}-openssh-container",
            repository_name=f"{name}_openssh_image",
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )
        
        openssh_container_repository.add_to_resource_policy(
            statement=our_statement
        )
        
        shiny_container_repository = ecr.Repository(
            scope=self,
            id=f"{name}-shiny-container",
            repository_name=f"{name}_shiny_image",
            removal_policy=RemovalPolicy.DESTROY,
            image_scan_on_push=True,
        )

        shiny_container_repository.add_to_resource_policy(
            statement=our_statement
        )
 

        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{name}-container--pipeline",
            pipeline_name=f"{name}"
        )

        """
        # Outputs
        cdk.CfnOutput(
            scope=self,
            id="application_repository",
            value=codecommit_repo.repository_clone_url_http
        )
        """
        source_output = codepipeline.Artifact()
        docker_output = codepipeline.Artifact(artifact_name="Docker")

        buildspec_docker = codebuild.BuildSpec.from_source_filename("buildspec.yml")

        dockerid = sm.Secret.from_secret_name_v2(
                self, 
                "ImportedDockerId",
                secret_name="ImportedDockerId"
                )
                
        docker_build = codebuild.PipelineProject(
            scope=self,
            id=f"DockerBuild",
            environment=dict(
                build_image=codebuild.LinuxBuildImage.STANDARD_4_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                privileged=True),
            environment_variables={
                'RSTUDIO_REPO_ECR': codebuild.BuildEnvironmentVariable(
                    value=rstudio_container_repository.repository_uri),
                'OPENSSH_REPO_ECR': codebuild.BuildEnvironmentVariable(
                    value=openssh_container_repository.repository_uri),
                'SHINY_REPO_ECR': codebuild.BuildEnvironmentVariable(
                    value=shiny_container_repository.repository_uri),
                'DOCKER_HUB_USERNAME': codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f'{dockerid.secret_name}:username'),
                'DOCKER_HUB_PASSWORD': codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f'{dockerid.secret_name}:password'),    
                'AWS_DEFAULT_ACCOUNT': codebuild.BuildEnvironmentVariable(
                    value=self.account),
                'AWS_DEFAULT_REGION': codebuild.BuildEnvironmentVariable(
                    value=self.region),
            },
            build_spec=buildspec_docker
        )

        rstudio_container_repository.grant_pull_push(docker_build)
        openssh_container_repository.grant_pull_push(docker_build)
        shiny_container_repository.grant_pull_push(docker_build)
        #pro_container_repository.grant_pull_push(docker_build)
        dockerid.grant_read(docker_build)
        
        docker_build.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
            resources=[f"arn:{cdk.Stack.of(self).partition}:ecr:{cdk.Stack.of(self).region}:{cdk.Stack.of(self).account}:repository/*"],))

        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit_Source",
            repository=codecommit_repo,
            output=source_output,
            branch="master"
        )

        
        
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Stages in CodePipeline
        pipeline.add_stage(
            stage_name="DockerBuild",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name=f"DockerBuild_and_Push_ECR",
                    project=docker_build,
                    input=source_output,
                    outputs=[docker_output])
            ]
        )