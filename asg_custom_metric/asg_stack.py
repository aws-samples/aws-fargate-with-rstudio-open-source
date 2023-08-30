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
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
import json
from aws_cdk import (
    Stack,
    Tags,
    Duration,
    Aws,
    Fn,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_cloudwatch as cw,
    aws_efs as efs,
)
from constructs import Construct


class AsgStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        res_name: str,
        instance: str,
        vpc: ec2.Vpc,
        config: list,
        lb_arn: str,
        lb_dns: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        global ami_name, name_space, metric_name, dimension_name, dimension_value, threshold_value, metric_granularity_min, collection_interval

        ami_name = config["ami_name"]
        name_space = config["metric"]["name_space"]
        name_space = f"{res_name}:{name_space}"
        metric_name = config["metric"]["metric_name"]
        dimension_name = config["metric"]["dimension_name"]
        dimension_value = config["metric"]["dimension_value"]
        threshold_value = config["metric"]["threshold_value"]
        metric_granularity_min = config["metric"]["metric_granularity_min"]
        if int(metric_granularity_min) > 1:
            collection_interval = f"*/{metric_granularity_min}"
        elif int(metric_granularity_min) == 1:
            collection_interval = "*"

        # Import Objects
        cert_arn, endpoint_sec_grp = self.import_objs(instance, config)

        # Create the security groups
        asg_security_group = self.create_security_groups(
            res_name, instance, config, vpc
        )

        # Create instance Roles
        asg_role = self.create_asg_role(res_name, instance, config, cert_arn)

        # Create EFS volume
        efs_file_system_share, access_point = self.create_efs(
            res_name, instance, config, asg_security_group, asg_role
        )

        # Create init data
        asg_init = self.init_data(
            res_name, instance, config, efs_file_system_share, access_point
        )

        # Create asg instances
        asg_inst = self.create_asg_inst(
            res_name,
            instance,
            config,
            ami_name,
            vpc,
            asg_security_group,
            endpoint_sec_grp,
            asg_role,
            asg_init,
        )

        # Configure listeners and target groups
        target_group, tls_tg = self.create_tg(
            res_name, instance, config, vpc, asg_inst, lb_arn, lb_dns, cert_arn
        )

        # Configure cloudwatch alarmssubnet
        healthy_instance_alarm = self.create_cw_alarm(res_name, instance, target_group)

    # Import Objects from other stacks
    def import_objs(self, instance, config):
        # Import TLS Certificate ARN
        cert_arn = config["cert_arn"]

        # Import vpc endpoint security group
        endpoint_sec_grp_id = Fn.import_value("security-group")

        endpoint_sec_grp = ec2.SecurityGroup.from_security_group_id(
            self,
            f"VPC-endpoint-Security-Group-{instance}",
            endpoint_sec_grp_id,
        )
        return cert_arn, endpoint_sec_grp

    # Create required role for servers
    def create_asg_role(self, res_name, instance, config, cert_arn):
        asg_role = iam.Role(
            self,
            f"{res_name}ASGRole{instance}",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchAgentServerPolicy"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "ElasticLoadBalancingFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCloudFormationReadOnlyAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonElasticFileSystemFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCertificateManagerFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonRoute53FullAccess"
                ),
            ],
        )

        # Allow nodes to read SSM parameters
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetParameter", "ssm:GetParametersByPath"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/{res_name}/{instance}/*"
                ],
            )
        )

        # Allow to describe the instances and tags
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ec2:DescribeInstances", "ec2:DescribeTags"],
                resources=["*"],
            )
        )

        # Allow to create cloudwatch logs
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                resources=["*"],
            )
        )

        # Policies required for the elasticity
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticloadbalancing:*",
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:SetInstanceProtection",
                    "autoscaling:RemoveInstanceProtection",
                    "cloudwatch:PutMetricData",
                ],
                resources=["*"],
            )
        )

        # Allow ACM certificate import
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "acm:ImportCertificate",
                    "acm:ListCertificates",
                    "acm:DescribeCertificate",
                ],
                resources=[cert_arn],
            )
        )

        # Allow ASG self update
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["autoscaling:UpdateAutoScalingGroup"],
                resources=[
                    "arn:aws:autoscaling:*:*:autoScalingGroup:*:autoScalingGroupName/*"
                ],
                conditions={
                    "StringEquals": {
                        f"autoscaling:ResourceTag/{config['tag_name']}": config[
                            "tag_value"
                        ]
                    },
                },
            ),
        )

        # Allow KMS Access
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kms:DescribeCustomKeyStores",
                    "kms:ListKeys",
                    "kms:ListAliases",
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:Describe*",
                ],
                resources=["*"],
            )
        )

        # Allow EFS Access
        asg_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticfilesystem:ClientWrite",
                    "elasticfilesystem:ClientMount",
                    "elasticfilesystem:ClientRoot",
                ],
                resources=["*"],
            )
        )

        return asg_role

    # Fuction to create security groups
    def create_security_groups(self, res_name, instance, config, vpc):
        asg_security_group = ec2.SecurityGroup(
            self,
            f"{res_name}-SG-{instance}",
            description=f"SecurityGroup for {res_name} - {instance}",
            vpc=vpc,
            allow_all_outbound=True,
        )
        # VPC
        asg_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(int(config["listen_port"]))
        )
        asg_security_group.add_ingress_rule(
            asg_security_group,
            ec2.Port.all_traffic(),
            "Cross instance communication",
        )
        asg_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "SSH",
        )

        return asg_security_group

    # Create launch template and asg
    def create_asg_inst(
        self,
        res_name,
        instance,
        config,
        ami_name,
        vpc,
        asg_security_group,
        endpoint_sec_grp,
        asg_role,
        asg_init,
    ):
        ami = ec2.LookupMachineImage(name=ami_name)

        # Userdata of the instances
        instance_userdata = ec2.UserData.for_linux()

        # Launch Template
        lt = ec2.LaunchTemplate(
            self,
            f"{res_name}-LT-{instance}",
            machine_image=ami,
            instance_type=ec2.InstanceType.of(
                getattr(ec2.InstanceClass, config["ec2_type"]),
                getattr(ec2.InstanceSize, config["ec2_size"]),
            ),
            user_data=instance_userdata,
            security_group=asg_security_group,
            role=asg_role,
        )

        lt.connections.add_security_group(endpoint_sec_grp)

        # ASG
        asg_inst = autoscaling.AutoScalingGroup(
            self,
            f"{res_name}-ASG-{instance}",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                one_per_az=True,
                subnet_type=getattr(ec2.SubnetType, config["asg_subnet_type"]),
            ),
            desired_capacity=int(config["asg-scale-up"]["desired_capacity"]),
            min_capacity=int(config["asg-scale-up"]["min_capacity"]),
            max_capacity=int(config["asg-scale-up"]["max_capacity"]),
            launch_template=lt,
            init=asg_init,
            update_policy=autoscaling.UpdatePolicy.replacing_update(),
            signals=autoscaling.Signals.wait_for_all(
                timeout=Duration.minutes(
                    int(config["asg-scale-up"]["timeout_duration"])
                ),
            ),
            new_instances_protected_from_scale_in=True,
        )

        Tags.of(asg_inst).add(config["tag_name"], config["tag_value"])

        asg_inst.node.add_dependency(lt)

        # Create a step-scaling policy according to custom metric
        tcp_conn_metric = cw.Metric(
            namespace=name_space,
            metric_name=metric_name,
            dimensions_map={
                dimension_name: dimension_value,
            },
            region=self.region,
            statistic="max",
            period=Duration.minutes(int(metric_granularity_min)),
        )

        asg_inst.scale_on_metric(
            "ScaleToTCpConns",
            metric=tcp_conn_metric,
            scaling_steps=[
                {"lower": int(threshold_value), "change": +1},
                {"lower": 1000, "change": +1},
            ],
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            cooldown=Duration.minutes(int(config["asg-scale-up"]["cooldown_duration"])),
        )

        return asg_inst

    # Configure listeners and target groups
    def create_tg(
        self, res_name, instance, config, vpc, asg_inst, lb_arn, lb_dns, cert_arn
    ):
        lb = elbv2.NetworkLoadBalancer.from_network_load_balancer_attributes(
            self,
            f"{res_name}-imported-lb-{instance}",
            load_balancer_arn=lb_arn,
            load_balancer_dns_name=lb_dns,
            vpc=vpc,
        )

        # Add TLS listener
        tls_listener = lb.add_listener(
            f"{res_name}-ListenerTLS-{instance}",
            port=int(config["listen_port"]),
            protocol=elbv2.Protocol.TLS,
            certificates=[elbv2.ListenerCertificate.from_arn(config["cert_arn"])],
            ssl_policy=elbv2.SslPolicy.RECOMMENDED,
        )

        # Add Target Group
        target_group = elbv2.NetworkTargetGroup(
            self,
            f"{res_name}-Target-{instance}",
            vpc=vpc,
            port=int(config["listen_port"]),
            target_group_name=f"{res_name}-TargetGroup-{instance}",
            health_check=elbv2.HealthCheck(
                port=config["healthcheck_port"], protocol=elbv2.Protocol.TCP
            ),
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.Protocol.TCP,
            preserve_client_ip=True,
            targets=[asg_inst],
        )

        tls_tg = tls_listener.add_target_groups("AsgTargetGroup", target_group)

        return target_group, tls_tg

    # Configure Cloudwatch Alarms
    def create_cw_alarm(self, res_name, instance, target_group):
        healthy_instance_metric = cw.Metric(
            namespace="AWS/NetworkELB",
            metric_name="HealthyHostCount",
            period=Duration.minutes(5),
            statistic="Minimum",
            dimensions_map={"TargetGroup": target_group.target_group_full_name},
        )

        healthy_instance_alarm = cw.Alarm(
            self,
            f"not-enough-{res_name}-instance-alarm-{instance}",
            comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD,
            metric=healthy_instance_metric,
            evaluation_periods=2,
            threshold=2,
        )

        Tags.of(healthy_instance_alarm).add("Name", "instance_count_alarm")

        return healthy_instance_alarm

    # Configure ec2 init, apply cloudwatch agent config
    def init_data(
        self, res_name, instance, config, efs_file_system_share, access_point
    ):
        applied_config_sets = [
            "configure_cli",
            "configure_cloudwatch",
            "create_custom_metric",
            "configure_cron",
            "configure_efs",
            "check_signal",
        ]

        file_path = config["log_file_path"]
        listen_port = config["listen_port"]

        asg_init = ec2.CloudFormationInit.from_config_sets(
            config_sets={
                # Applies the configs below in this order
                "default": applied_config_sets
            },
            configs={
                "configure_cli": ec2.InitConfig(
                    [
                        ec2.InitPackage.yum("curl"),
                        ec2.InitPackage.yum("unzip"),
                        ec2.InitCommand.shell_command(
                            """curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && export PATH=/usr/local/bin:$PATH && rm -rf aws awscliv2.zip"""
                        ),
                        ec2.InitCommand.shell_command(
                            f"aws configure set region {self.region}"
                        ),
                    ]
                ),
                "configure_cloudwatch": ec2.InitConfig(
                    [
                        ec2.InitPackage.yum("amazon-cloudwatch-agent"),
                        ec2.InitCommand.shell_command(
                            "amazon-linux-extras install epel -y"
                        ),
                        ec2.InitCommand.shell_command(
                            "amazon-linux-extras install collectd -y"
                        ),
                        ec2.InitFile.from_asset(
                            "/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
                            "resources/amazon-cloudwatch-agent.json",
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##log_file_path##/{file_path}/gi' /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##res_name##/{res_name}/gi' /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##instance##/{instance}/gi' /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
                        ),
                        ec2.InitCommand.shell_command(
                            'echo "Stopping CloudWatch agent" && /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a stop'
                        ),
                        ec2.InitCommand.shell_command(
                            """echo "Starting CloudWatch agent" && /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s > /var/log/aws-cloudwatch-agent-start.log"""
                        ),
                    ]
                ),
                "create_custom_metric": ec2.InitConfig(
                    [
                        ec2.InitPackage.yum("jq"),
                        ec2.InitCommand.shell_command("python3 -m pip install boto3"),
                        ec2.InitFile.from_asset(
                            "/opt/aws/custom_metric.py", "resources/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"""chmod u+x /opt/aws/custom_metric.py"""
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##PORT##/{listen_port}/gi' /opt/aws/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##NAME_SPACE##/{name_space}/gi' /opt/aws/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##METRIC_NAME##/{metric_name}/gi' /opt/aws/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##DIMENSION_NAME##/{dimension_name}/gi' /opt/aws/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##DIMENSION_VALUE##/{dimension_value}/gi' /opt/aws/custom_metric.py"
                        ),
                        ec2.InitCommand.shell_command(
                            f"sed -i 's/##THRESHOLD##/{threshold_value}/gi' /opt/aws/custom_metric.py"
                        ),
                    ]
                ),
                "configure_cron": ec2.InitConfig(
                    [
                        ec2.InitCommand.shell_command(
                            f"""echo "{collection_interval} * * * * /opt/aws/custom_metric.py ENABLE>/dev/null 2>&1" > /opt/aws/mycron && crontab /opt/aws/mycron"""
                        ),
                    ]
                ),
                "configure_efs": ec2.InitConfig(
                    [
                        ec2.InitPackage.yum("amazon-efs-utils"),
                        ec2.InitPackage.yum("nfs-utils"),
                        ec2.InitCommand.shell_command(
                            f"mkdir -p /{res_name}/efs/{instance}"
                        ),
                        ec2.InitCommand.shell_command(
                            f"""echo "{efs_file_system_share.file_system_id}:/ /{res_name}/efs/{instance} efs _netdev,noresvport,nofail,tls,iam,accesspoint={access_point.access_point_id} 0 0" >> /etc/fstab"""
                        ),
                        ec2.InitCommand.shell_command("mount -a --verbose"),
                        ec2.InitCommand.shell_command(
                            f"""MyInstID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id) && mkdir -p /{res_name}/efs/{instance}/$MyInstID"""
                        ),
                    ]
                ),
                "check_signal": ec2.InitConfig(
                    [
                        ec2.InitCommand.shell_command(
                            f"""MyInstID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id) && ASGLOGICALID=$(aws ec2 describe-instances --instance-ids $MyInstID --query "Reservations[].Instances[].Tags[?Key=='aws:cloudformation:logical-id'].Value" --output text) && /opt/aws/bin/cfn-signal -e $? --stack {Aws.STACK_NAME} --resource $ASGLOGICALID --region {Aws.REGION}"""
                        ),
                    ]
                ),
            },
        )

        return asg_init

    # Create EFS Volume
    def create_efs(self, res_name, instance, config, asg_security_group, asg_role):
        efs_security_group_share = ec2.SecurityGroup.from_security_group_id(
            self,
            f"efs-security-group-id-{res_name}-{instance}",
            Fn.import_value(f"efs-security-group-id-{res_name}-{instance}"),
            mutable=True,
        )

        efs_file_system_share = efs.FileSystem.from_file_system_attributes(
            self,
            f"Shiny-Fargate-EFS-File-System-Share-{res_name}-{instance}",
            file_system_id=Fn.import_value(f"efs-file-system-id-{res_name}-{instance}"),
            security_group=efs_security_group_share,
        )

        access_point = efs.AccessPoint.from_access_point_attributes(
            self,
            id=f"efs-access-point-id-{res_name}-{instance}",
            access_point_id=Fn.import_value(
                f"efs-access-point-id-{res_name}-{instance}"
            ),
            file_system=efs_file_system_share,
        )

        efs_file_system_share.connections.allow_default_port_from(asg_security_group)

        efs_file_system_share.grant(
            asg_role,
            "elasticfilesystem:ClientMount",
            "elasticfilesystem:ClientWrite",
            "elasticfilesystem:ClientRootAccess",
        )

        return efs_file_system_share, access_point
