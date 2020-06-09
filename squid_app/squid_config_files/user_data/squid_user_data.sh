#!/bin/bash -xe
# Redirect the user-data output to the console logs
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Apply the latest security patches
yum update -y --security

# Disable source / destination check. It cannot be disabled from the launch configuration
instanceid=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
aws ec2 modify-instance-attribute --no-source-dest-check --instance-id $instanceid --region ${AWS::Region}

# Install and start Squid
yum install -y squid
systemctl start squid || service squid start
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3129
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 3130

# Create a SSL certificate for the SslBump Squid module
mkdir /etc/squid/ssl
cd /etc/squid/ssl
openssl genrsa -out squid.key 4096
openssl req -new -key squid.key -out squid.csr -subj "/C=XX/ST=XX/L=squid/O=squid/CN=squid"
openssl x509 -req -days 3650 -in squid.csr -signkey squid.key -out squid.crt
cat squid.key squid.crt >> squid.pem

# Refresh the Squid configuration files from S3
mkdir /etc/squid/old
cat > /etc/squid/squid-conf-refresh.sh << 'EOF'
cp /etc/squid/* /etc/squid/old/
aws s3 sync s3://"${__S3BUCKET__}" /etc/squid
/usr/sbin/squid -k parse && /usr/sbin/squid -k reconfigure || (cp /etc/squid/old/* /etc/squid/; exit 1)
EOF
chmod +x /etc/squid/squid-conf-refresh.sh
/etc/squid/squid-conf-refresh.sh

# Schedule tasks
cat > ~/mycron << 'EOF'
* * * * * /etc/squid/squid-conf-refresh.sh
0 0 * * * sleep $(($RANDOM % 3600)); yum -y update --security
0 0 * * * /usr/sbin/squid -k rotate
EOF
crontab ~/mycron
rm ~/mycron

# Install and configure the CloudWatch Agent
rpm -Uvh https://amazoncloudwatch-agent-${AWS::Region}.s3.${AWS::Region}.amazonaws.com/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "agent": {
    "metrics_collection_interval": 10,
    "omit_hostname": true
  },
  "metrics": {
    "metrics_collected": {
      "procstat": [
        {
          "pid_file": "/var/run/squid.pid",
          "measurement": [
            "cpu_usage"
          ]
        }
      ]
    },
    "append_dimensions": {
      "AutoScalingGroupName": "${__CW_ASG__}"
    },
    "force_flush_interval": 5
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/squid/access.log*",
            "log_group_name": "/filtering-squid-instance/access.log",
            "log_stream_name": "{instance_id}",
            "timezone": "Local"
          },
          {
            "file_path": "/var/log/squid/cache.log*",
            "log_group_name": "/filtering-squid-instance/cache.log",
            "log_stream_name": "{instance_id}",
            "timezone": "Local"
          }
        ]
      }

    }
  }
}
EOF
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# CloudFormation signal
yum update -y aws-cfn-bootstrap
/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource "${__ASG__}" --region ${AWS::Region}