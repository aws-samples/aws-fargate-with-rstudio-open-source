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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
import os
import json
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks, NagSuppressions

import aws_cdk as cdk

from asg_custom_metric.pipeline_stack import PipelineStack

app = cdk.App()

with open("parameters.json", "r") as param_file:
    param_data = param_file.read()
CONFIG = json.loads(param_data)

instance = CONFIG["instance"]
res_name = CONFIG["resource_name"]

pipeline_build = PipelineStack(
    app,
    "PipelineStack",
    res_name=res_name,
    instance=instance,
    config=CONFIG,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
    ),
)

NagSuppressions.add_stack_suppressions(
    pipeline_build,
    [
        {
            "id": "AwsSolutions-S1",
            "reason": "The target S3 bucket for server access logs is user environment specefic.",
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": "In-built CDK product construct, not controlled from the code.",
        },
        {
            "id": "AwsSolutions-CB4",
            "reason": "A transient CodeBuild used by the pipeline for synthing the CDK.",
        },
    ],
)

Aspects.of(app).add(AwsSolutionsChecks())

app.synth()

cdk.Tags.of(app).add(CONFIG["tag_name"], CONFIG["tag_value"])
