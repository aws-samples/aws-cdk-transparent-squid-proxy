from aws_cdk import (
    aws_ec2 as ec2,
    core,
)

class VPCStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc_cidr: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC with 2 public and 2 isolated subnets across 2 availiability zones. 
        self.vpc = ec2.Vpc(self, "vpc",
            max_azs=2,
            cidr=vpc_cidr,
            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public",
                cidr_mask=24
                ), 
                ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.ISOLATED,
                name="Private",
                cidr_mask=24
                )
            ]
        )
        core.CfnOutput(self, "output-vpc-id",
                       value=self.vpc.vpc_id)