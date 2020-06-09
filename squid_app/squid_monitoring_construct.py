from aws_cdk import (
    core,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions
)


class SquidMonitoringConstruct(core.Construct):
    def __init__(self, scope: core.Construct, id: str, squid_asgs: list) -> None:
        super().__init__(scope, id)
        
        # SNS Topic for alarm
        self.squid_alarm_topic = sns.Topic(self,"squid-asg-alarm-topic", display_name='Squid ASG Alarm topic')

        # Create metric to use for triggering alarm when there is no CPU usage from the squid process
        for count, asg in enumerate(squid_asgs, start=1):
            squid_metric = cloudwatch.Metric(metric_name="procstat_cpu_usage",
                namespace='CWAgent',
                dimensions=dict(AutoScalingGroupName=asg.auto_scaling_group_name,
                    pidfile="/var/run/squid.pid",
                    process_name="squid")
            )

            # CloudWatch alarms to alert on Squid ASG issue
            squid_alarm = cloudwatch.Alarm(self,f"squid-alarm-{count}",
                alarm_description=f"Heart beat for Squid instance {count}",
                alarm_name=f"squid-alarm_{asg.auto_scaling_group_name}",
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
                metric=squid_metric,
                period=core.Duration.seconds(10),
                evaluation_periods=1,
                threshold=0.0,
                statistic='Average',
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING
            )
            squid_alarm.add_alarm_action(cw_actions.SnsAction(self.squid_alarm_topic))
            squid_alarm.add_ok_action(cw_actions.SnsAction(self.squid_alarm_topic))
