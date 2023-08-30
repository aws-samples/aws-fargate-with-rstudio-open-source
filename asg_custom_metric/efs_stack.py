from aws_cdk import (
    Stack,
    RemovalPolicy,
    Fn,
    CfnOutput as cfo,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_kms as kms,
)
from aws_cdk.aws_efs import Acl, PosixUser
from aws_cdk.aws_iam import AnyPrincipal, Effect, PolicyDocument, PolicyStatement
from constructs import Construct


class EFSVolumesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        res_name: str,
        instance: str,
        vpc: ec2.Vpc,
        config: list,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import KMS Key
        efs_kms_key_alias = kms.Alias.from_alias_name(
            self,
            "Efs-kms-key" + instance,
            alias_name=f"alias/efs-{instance}",
        )

        shared_efs = efs.FileSystem(
            self,
            "PGXNonProdSharedEFS",
            vpc=vpc,
            file_system_name="PGXNonProdSharedEFS",
            encrypted=True,
            kms_key=efs_kms_key_alias,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            enable_automatic_backups=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        shared_efs.node.default_child.file_system_policy = PolicyDocument(
            statements=[
                PolicyStatement(
                    effect=Effect.ALLOW,
                    principals=[AnyPrincipal()],
                    actions=[
                        "elasticfilesystem:ClientMount",
                        "elasticfilesystem:ClientWrite",
                        "elasticfilesystem:ClientRootAccess",
                    ],
                    conditions={
                        "Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}
                    },
                )
            ]
        )

        shared_access_point = shared_efs.add_access_point(
            f"SharedAccessPoint-{res_name}-{instance}",
            create_acl=Acl(
                owner_uid=config["efs"]["uid"],
                owner_gid=config["efs"]["gid"],
                permissions=config["efs"]["permission"],
            ),
            path=f"/{instance}",
            posix_user=PosixUser(uid=config["efs"]["uid"], gid=config["efs"]["gid"]),
        )

        cfo(
            self,
            f"efs-access-point-id-{res_name}-{instance}",
            export_name=f"efs-access-point-id-{res_name}-{instance}",
            value=shared_access_point.access_point_id,
        )

        # Export EFS details for other stacks
        cfo(
            self,
            f"efs-file-system-id-{res_name}-{instance}",
            export_name=f"efs-file-system-id-{res_name}-{instance}",
            value=shared_efs.file_system_id,
        )

        cfo(
            self,
            f"efs-security-group-id-{res_name}-{instance}",
            export_name=f"efs-security-group-id-{res_name}-{instance}",
            value=shared_efs.connections.security_groups[0].security_group_id,
        )
