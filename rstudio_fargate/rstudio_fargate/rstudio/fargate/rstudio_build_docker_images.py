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

from aws_cdk import core as cdk
from aws_cdk.core import Fn, RemovalPolicy,Duration,CfnOutput
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.aws_ecr import Repository


class RstudioBuildDockerImagesStack(cdk.Stack):
        def __init__(
            self, 
            scope: cdk.Construct, 
            id: str, 
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            rstudio_image_repo_name = self.node.try_get_context("rstudio_image_repo_name")

            if rstudio_image_repo_name is None:
                raise ValueError("Please provide rstudio docker image ecr repository name")

            ssh_image_repo_name = self.node.try_get_context("ssh_image_repo_name")

            if ssh_image_repo_name is None:
                raise ValueError("Please provide ssh server docker image ecr repository name")
            
            shiny_image_repo_name = self.node.try_get_context("shiny_image_repo_name")

            if shiny_image_repo_name is None:
                raise ValueError("Please provide shiny docker image ecr repository name")
                
            self.rstudio_asset = DockerImageAsset(
                self, 
                'Rstudio-image',
                directory="./docimage-rstudio",
                file='Dockerfile', 
                build_args={
                    'RSTUDIO_VERSION': '1.4.1103', 
                    'AWS_ACCOUNT': self.account,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': rstudio_image_repo_name
                    }
                )
            
            self.shiny_asset = DockerImageAsset(
                self, 
                'Shiny-image',
                directory="./docimage-shiny",
                file='Dockerfile', 
                build_args={
                    'AWS_ACCOUNT': self.account,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': shiny_image_repo_name
                    }
                )

            self.bastion_fg_asset = DockerImageAsset(
                self, 
                'Bastion-fg-image',
                directory="./docimage-openssh",
                file='Dockerfile', 
                build_args={
                    'AWS_ACCOUNT': self.account,
                    'AWS_REGION': self.region,
                    'IMAGE_REPO': ssh_image_repo_name
                    }     
                )
