from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_autoscaling_hooktargets as hooktargets,
    aws_iam as iam,
    aws_sns as sns,
    core
)

class SquidAsgConstruct(core.Construct):
    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, region: str) -> None:
        super().__init__(scope, id)
        
         # create an IAM role to attach to the squid instances
        squid_iam_role = iam.Role(self,"squid-role", 
          assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
          managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
          iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")]
        )
        
        # Add policy to allow EC2 update instance attributes
        squid_iam_role.add_to_policy(statement= iam.PolicyStatement(effect=iam.Effect.ALLOW,
            actions=['ec2:ModifyInstanceAttribute',],
            resources=['*']
            )
        )

        # Create bucket to hold Squid config and whitelist files
        squid_config_bucket = s3.Bucket(self,"squid-config",
                                encryption = s3.BucketEncryption.KMS_MANAGED)

        # Upload config and whiteliest files to S3 bucket
        s3_deployment.BucketDeployment(self,"config",
            destination_bucket=squid_config_bucket,
            sources=[s3_deployment.Source.asset(path='./squid_app/squid_config_files/config_files_s3')]
        )

        # Provide access to EC2 instance role to read and write to bucket
        squid_config_bucket.grant_read_write(identity=squid_iam_role)

        # Set the AMI to the latest Amazon Linux 2
        amazon_linux_2_ami = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        if vpc.public_subnets:
            # Squid ASGs with desired capacity as 1 Instance in each of the AZs 
            self.squid_asgs = []
            for count, az in enumerate(vpc.availability_zones, start=1):
                asg = autoscaling.AutoScalingGroup(self,f"asg-{count}",vpc=vpc,
                    instance_type=ec2.InstanceType("t3.nano"),
                    desired_capacity=1,
                    max_capacity=1,
                    min_capacity=1,
                    machine_image=amazon_linux_2_ami,
                    role=squid_iam_role,
                    vpc_subnets=ec2.SubnetSelection(
                        availability_zones=[az],
                        one_per_az=True,
                        subnet_type=ec2.SubnetType.PUBLIC
                        ),
                    health_check=autoscaling.HealthCheck.ec2(grace=core.Duration.minutes(5)),
                    resource_signal_count=1,
                    resource_signal_timeout=core.Duration.minutes(10)
                )

                cfn_asg : autoscaling.CfnAutoScalingGroup = asg.node.default_child 
                asg_logical_id = cfn_asg.logical_id

                # User data: Required parameters in user data script
                user_data_mappings = {"__S3BUCKET__": squid_config_bucket.bucket_name,
                                    "__ASG__": asg_logical_id,
                                    "__CW_ASG__": "${aws:AutoScalingGroupName}"
                                    }
                # Replace parameters with values in the user data
                with open("./squid_app/squid_config_files/user_data/squid_user_data.sh", 'r') as user_data_h:
                    # Use a substitution
                    user_data_sub = core.Fn.sub(user_data_h.read(), user_data_mappings)

                # Add User data to Launch Config of the autoscaling group
                asg.add_user_data(user_data_sub)
                
                # Security group attached to the ASG Squid instances
                # Outbound: All allowed
                # Inboud: Allowed from VPC CIDR on ports 80, 443)

                asg.connections.allow_from(other=ec2.Peer.ipv4(vpc.vpc_cidr_block),
                    port_range=ec2.Port(
                        protocol=ec2.Protocol.TCP,
                        string_representation="HTTP from VPC",
                        from_port=80,
                        to_port=80
                    )
                )

                asg.connections.allow_from(other=ec2.Peer.ipv4(vpc.vpc_cidr_block),
                    port_range=ec2.Port(
                        protocol=ec2.Protocol.TCP,
                        string_representation="HTTPS from VPC",
                        from_port=443,
                        to_port=443
                    )
                )

                # Create ASG Lifecycle hook to enable updating of route table using Lambda when instance launches and is marked Healthy

                autoscaling.LifecycleHook(self,f"asg-hook-{count}",
                    auto_scaling_group=asg,
                    lifecycle_transition=autoscaling.LifecycleTransition.INSTANCE_LAUNCHING,
                    notification_target=hooktargets.TopicHook(sns.Topic(self,f"squid-asg-{count}-lifecycle-hook-topic", 
                        display_name=f"Squid ASG {count} Lifecycle Hook topic")
                    ),
                    default_result=autoscaling.DefaultResult.ABANDON,
                    heartbeat_timeout=core.Duration.minutes(5)
                )

                # Tag ASG with the route table IDs used by the isolated and/or private subnets in the availability zone
                # This tag will be used by the Squid Lambda function to identify route tables to update when alarm changes from ALARM to OK

                private_subnets_in_az = []
                isolated_subnets_in_az = []
                route_table_ids = ''
                
                if vpc.private_subnets:
                    private_subnets_in_az = vpc.select_subnets(availability_zones=[az],
                        subnet_type=ec2.SubnetType.PRIVATE).subnets
                if vpc.isolated_subnets:
                    isolated_subnets_in_az = vpc.select_subnets(availability_zones=[az],
                        subnet_type=ec2.SubnetType.ISOLATED).subnets
                
                non_public_subnets_in_az = isolated_subnets_in_az + private_subnets_in_az

                # Loop through all non public subnets in AZ to identify route table and create a tag value string
                for subnet in non_public_subnets_in_az:
                    if route_table_ids:
                        route_table_ids=f"{route_table_ids},{subnet.route_table.route_table_id}"
                    else:
                        route_table_ids=subnet.route_table.route_table_id
                
                # Tag the ASG with route table ids
                core.Tags.of(asg).add(
                        key='RouteTableIds',
                        value=route_table_ids,
                        apply_to_launched_instances=False
                )

                self.squid_asgs.append(asg)
        
        else:
            raise ValueError("No public subnets in VPC")