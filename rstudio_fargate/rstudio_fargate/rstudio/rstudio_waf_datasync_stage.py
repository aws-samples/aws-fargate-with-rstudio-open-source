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

from aws_cdk import core
from aws_cdk import core as cdk

from .waf.rstudio_waf_stack import RstudioWafStack
from .datasync.rstudio_datasync_stack import RstudioDataSyncStack

class RstudioWafAndDatasyncStage (core.Stage):
    def __init__(self, scope: core.Construct, 
        id: str,
        instances: list,
        rstudio_account_ids: list,
        **kwargs):
        super().__init__(scope, id, **kwargs)

        
        env_dict={
                "account":self.account,
                "region":self.region,
            }

        
        for i in range(len(instances)):
            instance=instances[i]
            rstudio_account_id=rstudio_account_ids[i]
            env_dict={
                "account":rstudio_account_id,
                "region":self.region,
            }

            
            
            rstudio_waf_stack_build = RstudioWafStack(
                self, 
                'Waf-RstudioStack-' + instance,
                instance,
                env=env_dict,
            )
            
    
            rstudio_datasync_stack_build = RstudioDataSyncStack(
                self, 
                'Datasync-RstudioStack-' + instance,
                instance=instance,
                env=env_dict,
            )
            