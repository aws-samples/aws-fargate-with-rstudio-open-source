#!/usr/bin/env python3

"""
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2

class VpcStack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            instance = self.node.try_get_context("instance")

            if instance is None:
                raise ValueError("Please pass instance to use via context (dev/prod/...)")

            vpc_cidr = self.node.try_get_context("vpc_cidr_range")

            if vpc_cidr is None:
                raise ValueError("Please provide vpc cidr range for the build")

            self.vpc = ec2.Vpc(
                    self, 
                    'our-vpc-' + instance,
                    cidr=vpc_cidr,
                    max_azs=2,
                )