"""
Lambda handler to update ASG
"""
import boto3
import logging

from botocore.exceptions import ClientError
from botocore.config import Config
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class ASGdetails:
    desired = None
    maximum = None
    minimum = None
    name = None
    protected_from_scale_in = bool
    instance_ids = list()


def get_asg_details(tag_key, tag_value, region, config):
    asgs = list()
    client = boto3.client("autoscaling", region_name=region, config=config)
    try:
        response = (
            client.get_paginator("describe_auto_scaling_groups")
            .paginate()
            .build_full_result()
        )
    except ClientError as e:
        raise Exception(f"An error occurred when describing ASGs; exception: {e}")
    for asg in response.get("AutoScalingGroups"):
        # Determine if the ASG uses the tag to indicate the ASG we want
        for tag in asg.get("Tags"):
            if tag.get("Key") == tag_key and tag.get("Value") == tag_value:
                asg_details = ASGdetails()

                asg_details.name = asg.get("AutoScalingGroupName")
                asg_details.maximum = asg.get("MaxSize")
                asg_details.minimum = asg.get("MinSize")
                asg_details.desired = asg.get("DesiredCapacity")
                asg_details.protected_from_scale_in = asg.get(
                    "NewInstancesProtectedFromScaleIn"
                )
                asg_details.instance_ids = [
                    instance["InstanceId"] for instance in asg.get("Instances")
                ]

                asgs.append(asg_details)

                logger.info(f"Found ASG {asg_details.name}")
                break

    logger.info(f"Found {len(asgs)} ASGs")
    for asg in asgs:
        logger.info(
            f"Found {len(asg.instance_ids)} instances: {asg.instance_ids}  in asg: {asg.name}"
        )
    return asgs


def handler(event, context):
    # print event to logs
    logger.info(f"Called with {event}")
    config = Config(retries={"max_attempts": 10, "mode": "adaptive"})

    asg_client = boto3.client("autoscaling", region_name=event["region"], config=config)

    asgs = get_asg_details(
        event["tag_key"], event["tag_value"], event["region"], config
    )
    if event["scale_event"] == "UP":
        # Enable scale-in protection on ASG
        for asg in asgs:
            if (
                asg.minimum <= event["min_capacity"]
                and asg.maximum < event["max_capacity"]
                and asg.desired <= event["desired_capacity"]
            ):
                if asg.protected_from_scale_in == False:
                    logger.info(
                        f"Enabling instance termination protection on {asg.name}..."
                    )
                    try:
                        asg_response = asg_client.update_auto_scaling_group(
                            AutoScalingGroupName=asg.name,
                            NewInstancesProtectedFromScaleIn=True,
                        )
                        logger.info(asg_response)
                    except ClientError as e:
                        raise Exception(
                            f"An error occurred when updating ASG:{asg.name}; exception: {e}"
                        )
                    logger.info(
                        f"Enabled instance termination protection on {asg.name} ..."
                    )
                # Enable scale-in protection for ec2 instances
                # max batch size of set_instance_protection is 50
                batch_size = 50
                err = ""
                asg_response = ""
                for i in range(0, len(asg.instance_ids), batch_size):
                    batch = asg.instance_ids[i : i + batch_size]
                    logger.info(
                        f"Enabling scal-in protection on asg {asg.name} instances ..."
                    )
                    try:
                        asg_response = asg_client.set_instance_protection(
                            InstanceIds=batch,
                            AutoScalingGroupName=asg.name,
                            ProtectedFromScaleIn=True,
                        )
                        logger.info(asg_response)
                    except ClientError as e:
                        err = e.response["Error"]["Message"]
                        logger.info(
                            f"""Error enabling instance protection on instances for asg {asg.name} : {err}"""
                        )
                        raise Exception(
                            f"""Error enabling instance protection on instances for asg {asg.name} : {err}"""
                        )
                    logger.info(
                        f"Enabled instance termination protection on {asg.name} {[batch]}..."
                    )
                # Scale up ASG
                err = ""
                asg_response = ""
                logger.info(f"Setting scale up numbers on {asg.name} ...")
                try:
                    asg_response = asg_client.update_auto_scaling_group(
                        AutoScalingGroupName=asg.name,
                        MinSize=event["min_capacity"],
                        DesiredCapacity=event["desired_capacity"],
                        MaxSize=event["max_capacity"],
                    )
                except ClientError as e:
                    err = e.response["Error"]["Message"]
                    logger.info(
                        f"Error setting scale up numbers on asg: {asg.name} : {err}"
                    )
                    raise Exception(
                        f"Error setting scale up numbers on asg: {asg.name} : {err}"
                    )
                logger.info(f"Successfully set scale up numbers on asg: {asg.name}")
            else:
                logger.info(
                    f"Doing nothing ... Current min max or desired instance numbers are already above the provided scale up values in {asg.name}"
                )
    elif event["scale_event"] == "DOWN":
        # Disable scale-in protection on ASG
        for asg in asgs:
            if (
                asg.minimum >= event["min_capacity"]
                and asg.maximum > event["max_capacity"]
                and asg.desired >= event["desired_capacity"]
            ):
                if asg.protected_from_scale_in == True:
                    logger.info(
                        f"Disabling instance termination protection on {asg.name}..."
                    )
                    try:
                        asg_response = asg_client.update_auto_scaling_group(
                            AutoScalingGroupName=asg.name,
                            NewInstancesProtectedFromScaleIn=False,
                        )
                        logger.info(asg_response)
                    except ClientError as e:
                        raise Exception(
                            f"An error occurred when updating ASG:{asg.name}; exception: {e}"
                        )
                    logger.info(
                        f"Disabled instance termination protection on {asg.name} ..."
                    )

                # Disable scale-in protection on EC2 instances
                # max batch size of set_instance_protection is 50
                batch_size = 50
                err = ""
                asg_response = ""
                for i in range(0, len(asg.instance_ids), batch_size):
                    batch = asg.instance_ids[i : i + batch_size]
                    logger.info(
                        f"Disabling scal-in protection on asg {asg.name} instances ..."
                    )
                    try:
                        asg_response = asg_client.set_instance_protection(
                            InstanceIds=batch,
                            AutoScalingGroupName=asg.name,
                            ProtectedFromScaleIn=False,
                        )
                        logger.info(asg_response)
                    except ClientError as e:
                        err = e.response["Error"]["Message"]
                        logger.info(
                            f"Error disabling instance protection on instances for asg {asg.name} : {err}"
                        )
                        raise Exception(
                            f"Error disabling instance protection on instances for asg {asg.name} : {err}"
                        )
                    logger.info(
                        f"Disabled instance termination protection on {asg.name} {[batch]}..."
                    )

                # Scale Down ASG
                err = ""
                asg_response = ""
                logger.info(f"Setting scale down numbers on {asg.name} ...")
                try:
                    asg_response = asg_client.update_auto_scaling_group(
                        AutoScalingGroupName=asg.name,
                        MinSize=event["min_capacity"],
                        DesiredCapacity=event["desired_capacity"],
                        MaxSize=event["max_capacity"],
                    )
                except ClientError as e:
                    err = e.response["Error"]["Message"]
                    logger.info(
                        f"Error setting scale down numbers on asg: {asg.name} : {err}"
                    )
                    raise Exception(
                        f"Error setting scale down numbers on asg: {asg.name} : {err}"
                    )
                logger.info(f"Successfully set scale down numbers on asg: {asg.name}")
            else:
                logger.info(
                    f"Doing nothing ... Current min max or desired instance numbers are already below the provided scale down values in {asg.name}"
                )
