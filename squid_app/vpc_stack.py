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
            gateway_endpoints={ "S3": 
                ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.S3) },
            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public",
                cidr_mask=24
                ), 
                ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.ISOLATED,
                name="Isolated",
                cidr_mask=24
                )
            ]
        )
        # Add SSM VPC Endpoints to allow SSM communication to the test-instance.
        vpce_ssm = self.vpc.add_interface_endpoint("SSMvpce", 
            service=ec2.InterfaceVpcEndpointAwsService.SSM
        )
        vpce_ssmmsg = self.vpc.add_interface_endpoint("SSMMSGvpce", 
            service=ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES
        )
        vpce_cwlogs = self.vpc.add_interface_endpoint("CWLOGSvpce", 
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS
        )
        # this is a workaround to remove the incorrect auto-added tag (VPC name) to vpc endpoint children (security groups)
        for vpce in [vpce_ssm, vpce_ssmmsg, vpce_cwlogs]:
            core.Tags.of(vpce).remove("Name")

        core.CfnOutput(self, "output-vpc-id",
                       value=self.vpc.vpc_id)