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
    Stack,
    aws_codecommit as codecommit,
)
from constructs import Construct

from aws_cdk.pipelines import (
    CodePipeline,
    CodePipelineSource,
    ShellStep,
    CodeBuildOptions,
    CodeBuildStep,
)


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        res_name: str,
        instance: str,
        config: list,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        code_repo_name = config["code_repo_name"]

        code_repo = codecommit.Repository.from_repository_arn(
            self,
            f"{res_name}-{instance}",
            f"arn:aws:codecommit:{self.region}:{self.account}:{code_repo_name}",
        )

        app_pipeline = CodePipeline(
            self,
            f"Pipeline-{res_name}-{instance}",
            synth=ShellStep(
                "Synth",
                input=CodePipelineSource.code_commit(code_repo, "main"),
                commands=[
                    "npm install -g aws-cdk",
                    "pip install --upgrade pip",
                    "pip install -r requirements.txt",
                    "cdk synth",
                ],
            ),
        )

        app_stage = PipelineStage(
            self,
            "Deploy",
            res_name=res_name,
            instance=instance,
            config=config,
            env={
                "account": self.account,
                "region": self.region,
            },
        )

        app_deployment_stage = app_pipeline.add_stage(app_stage)
