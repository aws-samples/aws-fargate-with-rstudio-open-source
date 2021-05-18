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
from aws_cdk.core import Fn
from aws_cdk import aws_elasticloadbalancingv2 as alb
from aws_cdk import aws_wafv2 as waf
import jsii

class RstudioWafStack(cdk.Stack):
        def __init__(self, scope: cdk.Construct, id: str, 
                    instance: str,
                    rstudio_individual_container: bool,
                    **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            rstudio_users = self.node.try_get_context("rstudio_users")

            if rstudio_users is None:
                raise ValueError("Please provide comma-separated list of rstudio frontend users")
            
            allowed_ips = self.node.try_get_context("allowed_ips")
            allowed_ip_list=[]
            
            if allowed_ips is None:
                print("List of allowed IP addresses is not provided, will default to ALLOW all IPs")
            else:
                allowed_ip_list=allowed_ips.split(",")
                
            if allowed_ip_list == ['']: #IP list is empty
                is_allowed_ips_set=False
            else:
                is_allowed_ips_set=True
                
            waf_rules = []

            waf_rules.append(waf.CfnWebACL.RuleProperty(
                    name='Rstudio-AWSManagedRulesAdminProtectionRuleSet-' + instance,
                    statement=waf.CfnWebACL.StatementOneProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name='AWS',
                            name='AWSManagedRulesAdminProtectionRuleSet'
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name='Rstudio-AWSManagedRulesAdminProtectionRuleSet-' + instance
                    ),
                    priority=0,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={})
            ))

            waf_rules.append(waf.CfnWebACL.RuleProperty(
                    name='Rstudio-AWSManagedRulesAmazonIpReputationList-' + instance,
                    statement=waf.CfnWebACL.StatementOneProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name='AWS',
                            name='AWSManagedRulesAmazonIpReputationList'
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name='Rstudio-AWSManagedRulesAmazonIpReputationList-' + instance
                    ),
                    priority=1,
                    override_action=waf.CfnWebACL.OverrideActionProperty(none={})
            ))

            waf_rules.append(waf.CfnWebACL.RuleProperty(
                    name='Rstudio-RateLimitRule-' + instance,
                    statement=waf.CfnWebACL.StatementOneProperty(
                        rate_based_statement=waf.CfnWebACL.RateBasedStatementOneProperty(
                            aggregate_key_type="IP",
                            limit=1200					
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name='Rstudio-RateLimit-' + instance
                    ),
                    priority=2,
                    action=waf.CfnWebACL.RuleActionProperty(block={})  
            ))
            

            # Add IP whitelist bits here
            @jsii.implements(waf.CfnRuleGroup.IPSetReferenceStatementProperty)
            class IPSetReferenceStatement:
                @property
                def arn(self):
                    return self._arn
    
                @arn.setter
                def arn(self, value):
                    self._arn = value
                
            if is_allowed_ips_set:
                allowed_ipset = waf.CfnIPSet(
                    self,
                    'allowedipset',
                    description="allowedipset",
                    scope="REGIONAL",
                    addresses=allowed_ip_list,
                    ip_address_version="IPV4"
                )
                
                ip_set_ref_stmnt = IPSetReferenceStatement()
                ip_set_ref_stmnt.arn = allowed_ipset.attr_arn
                
                
                waf_rules.append(waf.CfnWebACL.RuleProperty(
                        name="allowiprule",
                        priority=3,
                        statement=waf.CfnWebACL.StatementOneProperty(
                            ip_set_reference_statement=ip_set_ref_stmnt
                        ),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            sampled_requests_enabled=True,
                            cloud_watch_metrics_enabled=False,
                            metric_name="webacl_ip_list_metric"
                        ),
                        action=waf.CfnWebACL.RuleActionProperty(
                            allow={}
                        )
                    )
                )
                
                rstudio_web_acl = waf.CfnWebACL(
                        self,
                        f'Rstudio-waf-web-acl-' + instance,      
                        default_action = waf.CfnWebACL.DefaultActionProperty(
                            block={}
                        ),
                        scope= 'REGIONAL',
                        visibility_config= waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name=f'rstudio-waf-' + instance,
                            sampled_requests_enabled=True
                        ),
                        rules= waf_rules
                )
                
                shiny_web_acl = waf.CfnWebACL(
                        self,
                        f'Shiny-waf-web-acl-' + instance,      
                        default_action = waf.CfnWebACL.DefaultActionProperty(
                            block={}
                        ),
                        scope= 'REGIONAL',
                        visibility_config= waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name=f'shiny-waf-' + instance,
                            sampled_requests_enabled=True
                        ),
                        rules= waf_rules
                )
            else:
                rstudio_web_acl = waf.CfnWebACL(
                        self,
                        f'Rstudio-waf-web-acl-' + instance,      
                        default_action = waf.CfnWebACL.DefaultActionProperty(
                            allow={}
                        ),
                        scope= 'REGIONAL',
                        visibility_config= waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name=f'rstudio-waf-' + instance,
                            sampled_requests_enabled=True
                        ),
                        rules= waf_rules
                )
            
                shiny_web_acl = waf.CfnWebACL(
                        self,
                        f'Shiny-waf-web-acl-' + instance,      
                        default_action = waf.CfnWebACL.DefaultActionProperty(
                            allow={}
                        ),
                        scope= 'REGIONAL',
                        visibility_config= waf.CfnWebACL.VisibilityConfigProperty(
                            cloud_watch_metrics_enabled=True,
                            metric_name=f'shiny-waf-' + instance,
                            sampled_requests_enabled=True
                        ),
                        rules= waf_rules
                )

            if rstudio_individual_container:
                number_of_users = len(rstudio_users.split(','))
                users=rstudio_users.split(",")
                for i in range(number_of_users):
                    username=users[i]
                    username_prefix = username.split('@')
                    #user_name=username.replace('@','').replace('.','-')
                    rstudio_load_balancer_arn= Fn.import_value(f'Rstudio-Fargate-Application-Load-Balancer-Arn-{instance}-'+ username_prefix[0].replace('.','-'))
                    rstudio_web_acl_assoc = waf.CfnWebACLAssociation(
                            self,
                            'Rstudio-WebAclAssociation-' + instance + '-' + username_prefix[0].replace('.','-'),
                            resource_arn=rstudio_load_balancer_arn, 
                            web_acl_arn= rstudio_web_acl.attr_arn,
                    )
            else:
                rstudio_load_balancer_arn= Fn.import_value(f'Rstudio-Fargate-Application-Load-Balancer-Arn-{instance}')
                
                rstudio_web_acl_assoc = waf.CfnWebACLAssociation(
                        self,
                        'Rstudio-WebAclAssociation-' + instance,
                        resource_arn=rstudio_load_balancer_arn, 
                        web_acl_arn= rstudio_web_acl.attr_arn,
                )

            
            shiny_load_balancer_arn= Fn.import_value(f'Shiny-Fargate-Application-Load-Balancer-Arn-{instance}')

            shiny_web_acl_assoc = waf.CfnWebACLAssociation(
                    self,
                    'Shiny-WebAclAssociation-' + instance,
                    resource_arn=shiny_load_balancer_arn, 
                    web_acl_arn= shiny_web_acl.attr_arn,
            )