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
    core as cdk,
    aws_route53 as r53,
    aws_certificatemanager as acm,
)
from aws_cdk.aws_route53 import RecordType, RecordTarget


class Route53Stack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        instance: str,
        r53_base_domain: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        build_domain = f"{instance}.{r53_base_domain}"
        build_zone = r53.PublicHostedZone(
            self,
            id=f"route53-build-zone-{instance}",
            zone_name=build_domain,
        )

        connect_domain = f"connect.{build_domain}"
        connect_zone = r53.PublicHostedZone(
            self,
            id=f"route53-connect-zone-{instance}",
            zone_name=connect_domain,
        )

        package_domain = f"package.{build_domain}"
        package_zone = r53.PublicHostedZone(
            self,
            id="route53-package-zone-{instance}",
            zone_name=package_domain,
        )

        recordset_connect_build = r53.RecordSet(
            self,
            id=f"ns-record-set-connect-{instance}",
            zone=build_zone,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*connect_zone.hosted_zone_name_servers),
            record_name=connect_domain,
        )

        recordset_package_build = r53.RecordSet(
            self,
            id=f"ns-record-set-package-{instance}",
            zone=build_zone,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*package_zone.hosted_zone_name_servers),
            record_name=package_domain,
        )

        imported_base = r53.HostedZone.from_lookup(
            self,
            id=f"base-hosted-zone-{instance}",
            domain_name=r53_base_domain,
        )

        recordset_base = r53.RecordSet(
            self,
            id=f"ns-record-set-base-{instance}",
            zone=imported_base,
            record_type=RecordType.NS,
            target=RecordTarget.from_values(*build_zone.hosted_zone_name_servers),
            record_name=build_domain,
        )

        cert_wildcard_domain = f"*.{build_domain}"
        cert = acm.Certificate(
            self,
            id=f"Connect-Certificate-{instance}",
            domain_name=cert_wildcard_domain,
            validation=acm.CertificateValidation.from_dns(build_zone),
        )

        recordset_connect_build.node.add_dependency(build_zone, connect_zone)
        recordset_package_build.node.add_dependency(build_zone, package_zone)
        recordset_base.node.add_dependency(
            recordset_connect_build, recordset_package_build
        )
        cert.node.add_dependency(recordset_base)

        # Pass domains and certificates to other stacks

        self.connect_hosted_zone_id = connect_zone.hosted_zone_id
        self.connect_hosted_zone_name = connect_zone.zone_name
        self.package_hosted_zone_id = package_zone.hosted_zone_id
        self.package_hosted_zone_name = package_zone.zone_name
        self.cert_arn = cert.certificate_arn
