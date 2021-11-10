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

import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="rstudio_fargate",
    version="0.0.1",
    description="RStudio/Shiny Open Source Project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="author",
    package_dir={"": "rstudio_fargate"},
    packages=setuptools.find_packages(where="rstudio_fargate"),
    install_requires=[
        "aws_cdk.core",
        "aws_cdk.aws_s3",
        "aws_cdk.aws_s3_notifications",
        "aws_cdk.aws_s3_deployment",
        "aws_cdk.aws_athena",
        "aws_cdk.aws_ec2",
        "aws_cdk.aws_ecs",
        "aws_cdk.aws_eks",
        "aws_cdk.aws_ecs-patterns",
        "aws_cdk.aws_certificatemanager",
        "aws_cdk.aws_route53",
        "aws_cdk.aws_route53_targets",
        "aws_cdk.aws_efs",
        "aws_cdk.aws_logs",
        "aws_cdk.aws_kms",
        "aws_cdk.aws_sns",
        "aws_cdk.aws_sns_subscriptions",
        "aws_cdk.aws_events",
        "aws_cdk.aws_events_targets",
        "aws_cdk.aws_elasticloadbalancingv2",
        "aws_cdk.aws_secretsmanager",
        "aws_cdk.aws_ecr_assets",
        "aws_cdk.aws_datasync",
        "aws_cdk.pipelines",
        "aws_cdk.aws_codepipeline",
        "aws_cdk.aws_codepipeline_actions",
        "aws_cdk.aws_codecommit",
        "aws_cdk.aws_codebuild",
        "aws_cdk.aws_wafv2",
        "cdk_nag",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
