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
    Stack,
    aws_ec2 as ec2,
)

from constructs import Construct


class VpcStack(Stack):
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

        vpc_cidr = config["vpc_cidr_range"]

        self.vpc = ec2.Vpc(
            self,
            id=f"{res_name}-vpc-{instance}",
            cidr=vpc_cidr,
            max_azs=2,
        )
