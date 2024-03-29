from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sns as sns
)

from squid_app.squid_asg_construct import SquidAsgConstruct
from squid_app.squid_monitoring_construct import SquidMonitoringConstruct
from squid_app.squid_lambda_construct import SquidLambdaConstruct

class SquidStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #  Create the core Squid components: 
        #  1. IAM instance profile to be used by the Squid instances
        #  2. S3 bucket to host Squid config and whitelist files
        #  3. Launch configuration with user data 
        #  4. Auto-Scaling Groups in each AZ with a Squid instance in the public subnet
        #  5. CloudWatch Log Groups to collect access and access logs from each instance in the ASGs
        
        asgs = SquidAsgConstruct(self,"squid-asgs", vpc=vpc, region=self.region)

        # Create the Lambda components
        #  1. IAM role for Lambda to assume
        #  2. Lambda function that is triggered when the alarm state changes 

        lambda_function = SquidLambdaConstruct(self,"squid-lambda")

        # Create the mmonitoring components
        #  1. Metrics and alarms for each ASG
        #  2. SNS topic where change in alarm state is published 

        monitoring = SquidMonitoringConstruct(self,"squid-monitoring", squid_asgs=asgs.squid_asgs)
        monitoring.node.add_dependency(lambda_function)

        # Add SNS subscription to tie the Lambda and CloudWatch alarm 
        lambda_function.add_sns_subscription(lambda_function=lambda_function.squid_alarm_lambda_function, squid_alarm_topic=monitoring.squid_alarm_topic)