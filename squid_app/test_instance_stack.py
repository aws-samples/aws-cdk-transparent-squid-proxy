from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    core,
)

class TestInstanceStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Set the AMI to the latest Amazon Linux 2
        amazon_linux_2_ami = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # Create a role for the instance and attach the SSM Managed Policy to this role.
        instance_role = iam.Role(self, "test-instance-SSM-role", 
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")]
        )

        # Create a test instance in any available private subnet allowing all outbound connections. No inbound connections allowed.
        instance = ec2.Instance(self, "test-instance",
            instance_type=ec2.InstanceType("t3.nano"),
            machine_image=amazon_linux_2_ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.ISOLATED
            ),
            role=instance_role,
            allow_all_outbound=True
            )

        core.CfnOutput(self, "output-instance-id",
                       value=instance.instance_id)