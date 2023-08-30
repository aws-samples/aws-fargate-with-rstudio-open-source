from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_route53 as r53,
    aws_acmpca as acmpca,
    CfnOutput as cfo,
)
from constructs import Construct


class AccountResourcesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        res_name: str,
        instance: str,
        vpc: ec2.Vpc,
        config: list,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Security Group to assosiated VPC Endpoints with. To be used across the account on EC2 instances
        sec_group = ec2.SecurityGroup(
            self,
            "EndPoint-SecGroup",
            vpc=vpc,
            description="Allow outbound traffic via AWS VPC Endpoints",
            allow_all_outbound=False,
        )

        # Define list of endpoints to create and assosiated resource names
        endpoints = {
            "SSM": ec2.InterfaceVpcEndpointAwsService.SSM,
            "SSMM": ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
            "CW": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH,
            "CWL": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            "EC2M": ec2.InterfaceVpcEndpointAwsService.EC2_MESSAGES,
            "SM": ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            "CFN": ec2.InterfaceVpcEndpointAwsService.CLOUDFORMATION,
            "ELB": ec2.InterfaceVpcEndpointAwsService.ELASTIC_LOAD_BALANCING,
            "STS": ec2.InterfaceVpcEndpointAwsService.STS,
            "EFS": ec2.InterfaceVpcEndpointAwsService.ELASTIC_FILESYSTEM,
            "KMS": ec2.InterfaceVpcEndpointAwsService.KMS,
        }

        # Create VPC Endpoints and assosiated them with our VPC and Security Group created above
        for id, ep in endpoints.items():
            ec2.InterfaceVpcEndpoint(
                self,
                id="Endpoint-{}".format(id),
                service=ep,
                vpc=vpc,
                security_groups=[sec_group],
            )

        # Create CloudFormation Output of the Security Group to be referenced in other stacks
        cfo(
            self,
            "EndPoint-SecGroup-Output",
            value=sec_group.security_group_id,
            description="Security Group for VPC Endpoints",
            export_name="security-group",
        )
