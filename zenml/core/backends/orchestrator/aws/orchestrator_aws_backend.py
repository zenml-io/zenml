import time
from typing import Text, List

import boto3
from botocore.exceptions import ClientError

from zenml.utils.logger import get_logger

logger = get_logger(__name__)


class OrchestratorAWSBackend:

    def __init__(self,
                 instance_name: Text = 'zenml',
                 instance_type: Text = 't2.micro',
                 image_id: Text = 'ami-001ec343bb21e7e59',
                 key_name: Text = 'baris',
                 min_count: int = 1,
                 max_count: int = 1,
                 security_groups: List = None):

        self.ec2_resource = boto3.resource('ec2')
        self.ec2_client = boto3.client('ec2')

        self.instance_name = instance_name
        self.instance_type = instance_type
        self.image_id = image_id
        self.key_name = key_name
        self.min_count = min_count
        self.max_count = max_count

        if security_groups is None:
            self.security_groups = ['zenml']
        else:
            self.security_groups = security_groups

    @staticmethod
    def make_unique_name(name):
        return f'{name}-{time.asctime()}'

    def get_key_pair_by_name(self,
                             name):
        key_pairs = self.ec2_client.describe_key_pairs()
        key_pair = [kp for kp in key_pairs['KeyPairs'] if
                    kp['KeyName'] == name]
        assert len(key_pair) == 1
        return key_pair[0]

    def setup_security_group(self,
                             group_name,
                             ssh_ingress_ip=None):

        try:
            default_vpc = list(self.ec2_resource.vpcs.filter(
                Filters=[{'Name': 'isDefault', 'Values': ['true']}]))[0]
            logger.info("Got default VPC %s.", default_vpc.id)
        except ClientError:
            logger.exception("Couldn't get VPCs.")
            raise
        except IndexError:
            logger.exception("No default VPC in the list.")
            raise

        try:
            security_group = default_vpc.create_security_group(
                GroupName=group_name,
                Description='demo security group')
            logger.info(
                "Created security group %s in VPC %s.", group_name,
                default_vpc.id)
        except ClientError:
            logger.exception("Couldn't create security group %s.", group_name)
            raise

        try:
            ip_permissions = [{
                # HTTP ingress open to anyone
                'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }, {
                # HTTPS ingress open to anyone
                'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
            if ssh_ingress_ip is not None:
                ip_permissions.append({
                    # SSH ingress open to only the specified IP address
                    'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
                    'IpRanges': [{'CidrIp': f'{ssh_ingress_ip}/32'}]})
            security_group.authorize_ingress(IpPermissions=ip_permissions)
            logger.info(
                "Set inbound rules for %s to allow all inbound HTTP and HTTPS "
                "but only %s for SSH.", security_group.id, ssh_ingress_ip)
        except ClientError:
            logger.exception("Couldnt authorize inbound rules for %s.",
                             group_name)
            raise
        else:
            return security_group

    def create_vm_instance(self):
        return self.ec2_resource.create_instances(
            ImageId=self.image_id,
            InstanceType=self.instance_type,
            SecurityGroups=self.security_groups,
            KeyName=self.key_name,
            MaxCount=self.max_count,
            MinCount=self.min_count)


i = OrchestratorAWSBackend()
OrchestratorAWSBackend().create_vm_instance()
print('Memories....')

# iam = boto3.client('iam')
# role = iam.get_role(RoleName='ZenML')
#
# print(role)
