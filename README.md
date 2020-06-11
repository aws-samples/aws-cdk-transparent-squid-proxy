
# AWS CDK Python project to deploy DNS filtering with Squid

This [AWS CDK](https://aws.amazon.com/cdk/) project deploys [Squid](http://www.squid-cache.org/) proxy instances to implement a “transparent proxy” that can restrict both HTTP and HTTPS outbound traffic to a given set of Internet domains, while being fully transparent for instances in the private subnet. 


>This project builds the soultion as described in the AWS Security blog: [How to add DNS filtering to your NAT instance with Squid](https://aws.amazon.com/blogs/security/how-to-add-dns-filtering-to-your-nat-instance-with-squid/). 

##### Architecture
In summary, the CDK project deploys a VPC with 2 public and 2 private subnets across 2 availability zones. Squid proxy instances in the public subnets intercept HTTP/S traffic and then initiate a connection with the destination through the Internet gateway. A test EC2 instance is provisioned in one private subnet

![Diagram](./img/squid-proxy-arch-diagram.png)

##### Addressing availability
The following diagram describes the solution used to address availability in case a Squid instance fails and traffic must be routed via the other available instance.

![Diagram](./img/squid-proxy-availability.png)


If a Squid instance fails, the instances in its associated private subnet cannot send outbound traffic anymore. To address this situation, each Squid instance is launched in an Amazon EC2 Auto Scaling group. 

A CloudWatch Agent on the Squid instance collects CPU usage of the Squid process. A CloudWatch alarm watches this metric and goes to an `ALARM` state when a data point is missing and a notification is sent to an Amazon Simple Notification Service (SNS) topic that triggers a Lambda function. The Lambda function marks the Squid instance as unhealthy in its Auto Scaling group, retrieves the list of healthy Squid instances based on the state of other CloudWatch alarms, and updates the route tables that currently route traffic to the unhealthy Squid instance to instead route traffic to the first available healthy Squid instance. 

While the Auto Scaling group automatically replaces the unhealthy Squid instance, private instances can send outbound traffic through the Squid instance in the other Availability Zone.

When the CloudWatch agent starts collecting the custom metric again on the replacement Squid instance, the alarm reverts to `OK` state. Similarly, CloudWatch sends a notification to the SNS topic, which then triggers the Lambda function. The Lambda function completes the lifecycle action to indicate that the replacement instance is ready to serve traffic, and updates the route table associated to the private subnet in the same availability zone to route traffic to the replacement instance.

## Deploying the solution 

Pre-requisites:

-	An AWS account
-	[AWS CLI, authenticated and configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
-	[Python 3.6+](https://www.python.org/downloads/)
-	[AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)
-	[Git](http://git-scm.com/downloads)


### 1: Clone the Git repository
```
git clone https://github.com/aws-samples/aws-cdk-transparent-squid-proxy 
```

### 2: Prepare context variables

[AWS CDK Context values](https://docs.aws.amazon.com/cdk/latest/guide/context.html) are key-value pairs that can be associated with a stack or construct. In this project they are used for some basic information required to deploy the solution. 

The `context` key in the `cdk.json` file is one of the ways that context values can be made available to the CDK app. 

Navigate to the cloned directory
```
$ cd aws-cdk-transparent-squid-proxy
```
Open the `cdk.json` file in a text editor and update the following values required by the CDK app:

 * **`account`**:    The AWS account number to deploy the stacks
 * **`region`**:     The AWS region to deploy the stacks
 * **`vpc_cidr`**:   The CIDR range to use for the VPC

Note that the `cdk.json` also states which Python command to use. Depending on your setup this may either be `python3` or `python`. Please update this if necessary for the `app` key in the `cdk.json` file.

`"app": "python app.py"`  **Or**  `"app": "python3 app.py"`

For all following steps `python` will be used. Replace if necessary

### 3. Create and activate the virtual environment

```
$ python -m venv .env
$ source .env/bin/activate
```

### 4. Install dependencies

```
$ pip install -r requirements.txt
```

### 5. Synthesize the templates
When CDK apps are executed, they produce (or “synthesize") an AWS CloudFormation template for each stack defined in the application. 

```
$ cdk synth
```
After this command executes successfully you can view the CloudFormation templates in the `cdk.out` folder

### 6. Bootstrap the environment
The first time you deploy an AWS CDK app into an environment (account/region), you’ll need to install a “bootstrap stack”. This stack includes resources that are needed for the CDK toolkit’s operation. For example, the stack includes an S3 bucket that is used to store templates and assets during the deployment proces

```
$ cdk bootstrap
```

### 7. Deploy the solution
Deply all stacks to your AWS account & region

When prompted, approve the request to allow CloudFormation to create IAM roles and security groups (Answer *y* to the question: *Do you wish to deploy these changes?*). 

If you want to override the approval prompts, add the **`--require-approval never`** option

```
$ cdk deploy "*"
```
This will begin the process of deploying the stacks. The deployment includes 3 stacks:
 * **VPC stack**:             A VPC across 2 AZs with 1 public and 1 private subnet in each AZ
 * **Squid stack**:           Squid instances in Auto Scaling Groups with required components to achieve high availablity. 
 * **Test instance stack**:   A test instance that can be accessed using AWS Systems Manager Session Manager
  

## Testing the solution
1. On the [AWS Systems Manager console](https://console.aws.amazon.com/systems-manager/): Choose **Session Manager**
2. Select the *test instance* and choose **Start Session**
3. After the connection is made, you can test the solution with the following commands. Only the last 2 requests should return a valid response, because Squid allows traffic to `*.amazonaws.com` only.
   1. `curl http://www.amazon.com`
   2. `curl https://www.amazon.com`
   3. `curl http://calculator.s3.amazonaws.com/index.html`
   4. `curl https://calculator.s3.amazonaws.com/index.html`

## Cleaning up
A CDK application can be destroyed by using the following command: 
```
$ cdk destroy "*"`
```
When asked to confirm the deletion of the 3 stacks, select “`y`”.