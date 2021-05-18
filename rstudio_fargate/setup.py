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

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "rstudio_fargate"},
    packages=setuptools.find_packages(where="rstudio_fargate"),

    install_requires=[
        "aws_cdk.core==1.100.0",
        "aws_cdk.aws_s3==1.100.0",
        "aws_cdk.aws_s3_notifications==1.100.0",
        "aws_cdk.aws_s3_deployment==1.100.0",
        "aws_cdk.aws_athena==1.100.0",
        "aws_cdk.aws_ec2==1.100.0",
        "aws_cdk.aws_ecs==1.100.0",
        "aws_cdk.aws_eks==1.100.0",
        "aws_cdk.aws_ecs-patterns==1.100.0",
        "aws_cdk.aws_certificatemanager==1.100.0",
        "aws_cdk.aws_route53==1.100.0",
        "aws_cdk.aws_route53_targets==1.100.0",
        "aws_cdk.aws_efs==1.100.0",
        "aws_cdk.aws_logs==1.100.0",
        "aws_cdk.aws_kms==1.100.0",
        "aws_cdk.aws_sns==1.100.0",
        "aws_cdk.aws_sns_subscriptions==1.100.0",
        "aws_cdk.aws_events==1.100.0",
        "aws_cdk.aws_events_targets==1.100.0",
        "aws_cdk.aws_elasticloadbalancingv2==1.100.0",
        "aws_cdk.aws_wafv2==1.100.0",
        "aws_cdk.aws_secretsmanager==1.100.0",
        "aws_cdk.aws_ecr_assets==1.100.0",
        "aws_cdk.aws_datasync==1.100.0",
        "aws_cdk.pipelines==1.100.0",
        "aws_cdk.aws_codepipeline==1.100.0",
        "aws_cdk.aws_codepipeline_actions==1.100.0",
        "aws_cdk.aws_codecommit==1.100.0",
        "aws_cdk.aws_codebuild==1.100.0",
        "cdk-ec2-key-pair==1.5.0"
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
