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
from ...custom.ses_custom_resource import SESSendEmail
from aws_cdk import core as cdk
from aws_cdk.core import Fn
from aws_cdk import aws_secretsmanager as sm
import aws_cdk.aws_kms as kms
from aws_cdk import aws_route53 as r53

class RstudioEmailPasswordsStack(cdk.Stack):
        def __init__(
            self, 
            scope: cdk.Construct, 
            id: str, 
            instance: str,
            rstudio_install_type: str, 
            rstudio_individual_container: bool,
            **kwargs) -> None:
            super().__init__(scope, id, **kwargs)

            rstudio_users = self.node.try_get_context("rstudio_users")

            if rstudio_users is None:
                raise ValueError("Please provide comma-separated list of rstudio frontend users")   

            sns_email = self.node.try_get_context("sns_email_id")

            if sns_email is None:
                raise ValueError("Please provide email id for sending pipeline failure notifications")

            counter=0 
            
            secretpass_arn=""
            users=rstudio_users.split(",")
    
            shiny_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                self, 
                'Shiny-zone-' + instance, 
                hosted_zone_id=Fn.import_value('Shiny-fg-instance-hosted-zone-id-' + instance),
                zone_name=Fn.import_value('Shiny-fg-instance-hosted-zone-name-' + instance)
                )

            shiny_url = f'https://{shiny_zone_fg.zone_name}'
                
            for i in range(len(users)):
                username=users[i] #Username is an email address
                username_prefix = username.split('@')
                user_name=username.replace('@','_').replace('.','_')
                context_string=f"{user_name}_pass_arn_{instance}"
                    
                arn_file = open("rstudio_arn.txt", "r")
                readarn = arn_file.readlines()
                for line in readarn:
                    arn_data = line.rstrip("\n").split(": ")
                    if arn_data[0] == context_string:
                        secretpass_arn = arn_data[1]
                        arn_file.close() 
                        # Get URL here
                        rstudio_url = ''
                        if rstudio_individual_container:
                            rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                self, 
                                'Rstudio-zone-individual-user-' + instance + '-' + username_prefix[0].replace('.','-'), 
                                hosted_zone_id=Fn.import_value('Rstudio-individual-hosted-zone-id-' + instance + '-' + username_prefix[0].replace('.','-')),
                                zone_name=Fn.import_value('Rstudio-individual-hosted-zone-name-' + instance + '-' + username_prefix[0].replace('.','-'))
                                )
                            rstudio_url=f'https://{rstudio_zone_fg.zone_name}'
                        else:
                            if rstudio_install_type == "fargate":
                                rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                    self, 
                                    'Rstudio-zone-fg-instance-' + instance + '-' + username_prefix[0].replace('.','-'), 
                                    hosted_zone_id=Fn.import_value('Rstudio-fg-instance-hosted-zone-id-' + instance),
                                    zone_name=Fn.import_value('Rstudio-fg-instance-hosted-zone-name-' + instance),
                                    )
                                rstudio_url=f'https://{rstudio_zone_fg.zone_name}'

                            if rstudio_install_type == "ec2":
                                rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                    self, 
                                    'Rstudio-zone-ec2-instance-' + instance + username_prefix[0].replace('.','-'), 
                                    hosted_zone_id=Fn.import_value('Rstudio-ec2-instance-hosted-zone-id-' + instance),
                                    zone_name=Fn.import_value('Rstudio-ec2-instance-hosted-zone-name-' + instance),
                                    )
                                rstudio_url=f'https://{rstudio_zone_fg.zone_name}'

                        # Send email here
                        ses_send_email =  SESSendEmail(
                            self,
                            id=f"SES-Send-User-{context_string}",
                            email_from = sns_email,
                            email_to = username,
                            secret_arn = secretpass_arn,
                            subject = "Welcome to RStudio",
                            message = f"""Hello {username},<br/><br/>Your password is: <password><br/><br/>
                                                To acess rstudio click {rstudio_url}<br/><br/>
                                                  To acess shiny click {shiny_url}<br/><br/>
                                            Regards,
                                            <br>Rstudio@{instance}""",
                            region = self.region,
                            account_id=self.account,
                            counter=counter,
                            instance=instance
                        )
                        counter+=1
                        break
                        
            if rstudio_individual_container:
                arn_file = open("rstudio_arn.txt", "r")
                readarn = arn_file.readlines()
                    
                users=rstudio_users.split(",")  

                for i in range(len(users)):
                    username=users[i]
                    username_prefix = username.split('@')
                    user_name=username.replace('@','_').replace('.','_')
                    context_string_rstudio=f"rstudio_{instance}_{user_name}_container_pass_arn"
                    arn_file = open("rstudio_arn.txt", "r")
                    readarn = arn_file.readlines()
                    for line in readarn:
                        arn_data = line.rstrip("\n").split(": ")
                        if arn_data[0] == context_string_rstudio:
                            secretpass_arn = arn_data[1]
                            arn_file.close() 
                            rstudio_url = ''
                            # Send email here
                            rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                self, 
                                'Rstudio-zone-individual' + instance + username_prefix[0].replace('.','-'), 
                                hosted_zone_id=Fn.import_value('Rstudio-individual-hosted-zone-id-' + instance + '-' + username_prefix[0].replace('.','-')),
                                zone_name=Fn.import_value('Rstudio-individual-hosted-zone-name-' + instance + '-' + username_prefix[0].replace('.','-'))
                                )
                            rstudio_url=f'https://{rstudio_zone_fg.zone_name}'
                            # Send email here
                            ses_send_email =  SESSendEmail(
                                self,
                                id=f"SES-Send-User-{context_string_rstudio}-Email",
                                email_from = sns_email,
                                email_to = sns_email,
                                secret_arn = secretpass_arn,
                                subject = "Welcome to RStudio",
                                message = f"""Hello rstudio,<br/><br/>The password for the default rstudio user for this container is: <password><br/><br/>
                                                  To acess rstudio click {rstudio_url}<br/><br/>
                                                  To acess shiny click {shiny_url}<br/><br/>
                                                  Regards,<br>Rstudio@{instance}""",
                                region = self.region,
                                account_id=self.account,
                                counter=counter,
                                instance=instance
                            )
                            counter+=1
                            break                        
            else:
                context_string_rstudio=f"rstudio_{instance}_pass_arn"
                arn_file = open("rstudio_arn.txt", "r")
                readarn = arn_file.readlines()
                for line in readarn:
                    arn_data = line.rstrip("\n").split(": ")
                    if arn_data[0] == context_string_rstudio:
                        secretpass_arn = arn_data[1]
                        arn_file.close() 
                        rstudio_url = ''
                        # Get URL here
                        if rstudio_install_type == "fargate":
                            rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                self, 
                                'Rstudio-zone-fg-rstudiouser' + instance, 
                                hosted_zone_id=Fn.import_value('Rstudio-fg-instance-hosted-zone-id-' + instance),
                                zone_name=Fn.import_value('Rstudio-fg-instance-hosted-zone-name-' + instance),
                                )
                            rstudio_url=f'https://{rstudio_zone_fg.zone_name}'

                        if rstudio_install_type == "ec2":
                            rstudio_zone_fg = r53.PublicHostedZone.from_hosted_zone_attributes(
                                self, 
                                'Rstudio-zone-ec2-rstudiouser' + instance, 
                                hosted_zone_id=Fn.import_value('Rstudio-ec2-instance-hosted-zone-id-' + instance),
                                zone_name=Fn.import_value('Rstudio-ec2-instance-hosted-zone-name-' + instance),
                                )
                            rstudio_url=f'https://{rstudio_zone_fg.zone_name}'
                        # Send email here
                        ses_send_email =  SESSendEmail(
                            self,
                            id=f"SES-Send-rstudio-User-{context_string_rstudio}-Email",
                            email_from = sns_email,
                            email_to = sns_email,
                            secret_arn = secretpass_arn,
                            subject = "Welcome to RStudio",
                            message = f"""Hello rstudio,<br/><br/>The password for the default rstudio user for this container is: <password><br/><br/>
                                              To acess rstudio click {rstudio_url}<br/><br/>
                                              To acess shiny click {shiny_url}<br/><br/>
                                              Regards,<br>Rstudio@{instance}""",
                            region = self.region,
                            account_id=self.account,
                            counter=counter,
                            instance=instance
                        )
                        counter+=1
                        break
