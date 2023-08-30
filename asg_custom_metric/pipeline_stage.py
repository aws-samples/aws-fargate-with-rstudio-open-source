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

from .vpc_stack import VpcStack
from .account_stack import AccountResourcesStack
from .kms import KmsStack
from .efs_stack import EFSVolumesStack
from .nlb_stack import NlbStack
from .asg_stack import AsgStack
from .lambda_asg_update import LambdaAsgUpdateStack

from aws_cdk import (
    Stage,
    Fn,
)

from constructs import Construct


class PipelineStage(Stage):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        res_name: str,
        instance: str,
        config: list,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env_dict = {
            "account": self.account,
            "region": self.region,
        }

        vpc_stack_build = VpcStack(
            self,
            construct_id=f"{res_name}-VpcStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            env=env_dict,
        )

        account_stack_build = AccountResourcesStack(
            self,
            construct_id=f"{res_name}-AccountResourcesStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            vpc=vpc_stack_build.vpc,
            env=env_dict,
        )

        kms_stack_build = KmsStack(
            self,
            construct_id=f"{res_name}-KmsStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            env=env_dict,
        )

        efs_stack_build = EFSVolumesStack(
            self,
            construct_id=f"{res_name}-EFSVolumesStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            vpc=vpc_stack_build.vpc,
            env=env_dict,
        )

        nlb_stack_build = NlbStack(
            self,
            construct_id=f"{res_name}-NlbStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            vpc=vpc_stack_build.vpc,
            env=env_dict,
        )

        asg_stack_build = AsgStack(
            self,
            construct_id=f"{res_name}-AsgStack-{instance}",
            res_name=res_name,
            instance=instance,
            config=config,
            vpc=vpc_stack_build.vpc,
            lb_arn=nlb_stack_build.lb_arn,
            lb_dns=nlb_stack_build.lb_dns,
            env=env_dict,
        )

        lambda_stack_build = LambdaAsgUpdateStack(
            self,
            construct_id=f"{res_name}-LambdaAsgUpdateStack-{instance}",
            res_name=res_name,
            instance=instance,
            vpc=vpc_stack_build.vpc,
            config=config,
            env=env_dict,
        )

        account_stack_build.add_dependency(vpc_stack_build)

        kms_stack_build.add_dependency(account_stack_build)

        efs_stack_build.add_dependency(kms_stack_build)

        asg_stack_build.add_dependency(efs_stack_build)

        lambda_stack_build.add_dependency(asg_stack_build)
