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
from .ses_custom_resource import SESSendEmail

from aws_cdk import (
    core as cdk,
    aws_secretsmanager as sm,
    aws_kms as kms,
    aws_route53 as r53,
)


class RstudioEmailPasswordsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        rstudio_hosted_zone_id: str,
        rstudio_hosted_zone_name: str,
        shiny_hosted_zone_id: str,
        shiny_hosted_zone_name: str,
        sns_email: str,
        secretpass_arn: list,
        number_of_rstudio_containers: int,
        rstudio_user_key_alias: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        sns_email = self.node.try_get_context("sns_email_id")

        rstudio_zone = r53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            id=f"RStudio-zone-{instance}",
            hosted_zone_id=rstudio_hosted_zone_id,
            zone_name=rstudio_hosted_zone_name,
        )

        rstudio_url = f"https://{rstudio_zone.zone_name}"

        shiny_zone = r53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            id=f"Shiny-zone-{instance}",
            hosted_zone_id=shiny_hosted_zone_id,
            zone_name=shiny_hosted_zone_name,
        )

        shiny_url = f"https://{shiny_zone.zone_name}"

        # Send email here
        for i in range(1, number_of_rstudio_containers + 1):
            rstudio_url = f"https://container{i}.{rstudio_zone.zone_name}"
            ses_send_email = SESSendEmail(
                self,
                id=f"SES-Send-container{i}-{instance}",
                email_from=sns_email,
                email_to=sns_email,
                secret_arn=secretpass_arn[i - 1],
                subject="Welcome to RStudio",
                message=f"""Hello rstudio@container{i},<br/><br/>Your username is: rstudio <br/>
                                                Your password is: <password><br/><br/>
                                                To acess rstudio click {rstudio_url}<br/><br/>
                                                  To acess shiny click {shiny_url}<br/><br/>
                                                  In RStudio, save shiny app files in: /srv/shiny-server to deploy shiny apps.<br/><br/>
                                            Regards,
                                            <br>Rstudio@container{i}.{instance}""",
                region=self.region,
                account_id=self.account,
                counter=i,
                instance=instance,
                rstudio_user_key_alias=rstudio_user_key_alias,
            )
