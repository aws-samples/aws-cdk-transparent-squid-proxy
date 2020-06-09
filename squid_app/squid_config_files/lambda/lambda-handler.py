import json
import boto3
import os

as_client = boto3.client('autoscaling')
cw_client = boto3.client('cloudwatch')
ec2_client = boto3.client('ec2')

# Function to create or update the default route
def update_route(route_table_id, instance_id, asg_name):
  parameters = {
    'DestinationCidrBlock': '0.0.0.0/0',
    'RouteTableId': route_table_id,
    'InstanceId': instance_id
  }
  try:
    ec2_client.replace_route(**parameters)
  except:
    ec2_client.create_route(**parameters)
  ec2_client.create_tags(
    Resources=[route_table_id],
    Tags=[{'Key': 'AutoScalingGroupName', 'Value': asg_name}]
  )
  print('Updated default route of %s to %s' % (route_table_id, instance_id))

def handler(event, context):
  print(json.dumps(event))
  for record in event['Records']:
    message = json.loads(record['Sns']['Message'])
    print('Alarm state: %s' % message['NewStateValue'])

    # Auto Scaling group associated to the alarm
    asg_name = message['AlarmName'].split('_')[1]
    print('ASG Name: %s' % asg_name)
    asg = as_client.describe_auto_scaling_groups(
      AutoScalingGroupNames=[asg_name]
    )['AutoScalingGroups'][0]

    # If the NAT instance has failed
    if message['NewStateValue'] == 'ALARM':

      # Set the NAT instance to Unhealthy
      try:
        for instance in asg['Instances']:
          as_client.set_instance_health(
            InstanceId=instance['InstanceId'],
            HealthStatus='Unhealthy'
          )
          print('Set instance %s to Unhealthy' % instance['InstanceId'])
      except:
        pass

      # Route traffic to the first health NAT instance
      for healthy_alarm in cw_client.describe_alarms(
        AlarmNamePrefix='squid-alarm_',
        ActionPrefix=os.environ.get('TOPIC_ARN'),
        StateValue='OK'
      )['MetricAlarms']:

        healthy_asg_name = healthy_alarm['AlarmName'].split('_')[1]
        healthy_asg = as_client.describe_auto_scaling_groups(
          AutoScalingGroupNames=[healthy_asg_name]
        )['AutoScalingGroups'][0]
        healthy_instance_id = healthy_asg['Instances'][0]['InstanceId']
        print('Healthy NAT instance: %s' % healthy_instance_id)

        # For each route table that currently routes traffic to the unhealthy NAT
        # instance, update the default route
        for route_table in ec2_client.describe_route_tables(
          Filters=[{'Name': 'tag:AutoScalingGroupName', 'Values': [asg_name]}]
        )['RouteTables']:
          update_route(route_table['RouteTableId'], healthy_instance_id, healthy_asg_name)

        break

    # If the NAT instance has recovered
    else:

      # ID of the NAT instance launched by the Auto Scaling group
      for instance in asg['Instances']:
        if instance['HealthStatus'] == 'Healthy':
          asg_instance_id = instance['InstanceId']
          break
      print('Instance launched by the ASG: %s' % asg_instance_id)

      # Complete the lifecycle action if the NAT instance was just launched
      lc_name = as_client.describe_lifecycle_hooks(
        AutoScalingGroupName=asg_name
      )['LifecycleHooks'][0]['LifecycleHookName']
      try:
        as_client.complete_lifecycle_action(
          LifecycleHookName=lc_name,
          AutoScalingGroupName=asg_name,
          LifecycleActionResult='CONTINUE',
          InstanceId=asg_instance_id
        )
        print('Lifecycle action completed')
      except:
        pass

      # Create or update the default route for each route table that should route 
      # traffic to this NAT instance in a nominal situation

      for route_table_id in as_client.describe_tags(
        Filters=[{'Name': 'auto-scaling-group', 'Values': [asg_name]},
                {'Name': 'key', 'Values': ['RouteTableIds']}]
        )['Tags'][0]['Value'].split(','):
        update_route(route_table_id, asg_instance_id, asg_name)