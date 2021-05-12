from aws_cdk import (
    core,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sns as sns
)


class SquidLambdaConstruct(core.Construct):
    def __init__(self, scope: core.Construct, id: str) -> None:
        super().__init__(scope, id)
        
        # Create IAM role for Lambda
        lambda_iam_role = iam.Role(self,"lambda-role", 
          assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
          managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")]
        )
        
        # Add policies to allow Lambda that allow it to update route tables of the VPC to point to a healthy Squid instance ENI
        lambda_iam_role.add_to_policy(statement= iam.PolicyStatement(effect=iam.Effect.ALLOW,
            actions=['ec2:ModifyInstanceAttribute',
                'autoscaling:Describe*',
                'autoscaling:CompleteLifecycleAction',
                'autoscaling:SetInstanceHealth',
                'cloudwatch:Describe*',
                'ec2:CreateRoute',
                'ec2:CreateTags',
                'ec2:ReplaceRoute',
                'ec2:Describe*',
                ],
            resources=['*']
            )
        )
    
        # Create a Lambda function that is triggered when the Squid Alarm state changes
        self.squid_alarm_lambda_function = _lambda.Function(self, "alarm-function",
                                    runtime=_lambda.Runtime.PYTHON_3_8,
                                    handler="lambda-handler.handler",
                                    code=_lambda.Code.asset("./squid_app/squid_config_files/lambda"),
                                    role=lambda_iam_role,
                                    timeout=core.Duration.seconds(60)
                                )

    def add_sns_subscription (self,
        lambda_function: _lambda.Function,
        squid_alarm_topic: sns.Topic
    ):
        lambda_function.add_environment(key="TOPIC_ARN", value = squid_alarm_topic.topic_arn)
        lambda_function.add_permission("squid-lambda-permission",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            action='lambda:InvokeFunction',
            source_arn=squid_alarm_topic.topic_arn
        )
        squid_alarm_topic.add_subscription(sns_subscriptions.LambdaSubscription(lambda_function))