
# CDK Python project to deploy DNS filtering with Squid

This CDK project deploys Squid proxy instances to implement a “transparent proxy” that can restrict both HTTP and HTTPS outbound traffic to a given set of Internet domains, while being fully transparent for instances in the private subnet. 

The solution follows the AWS Security blog: [How to add DNS filtering to your NAT instance with Squid](https://aws.amazon.com/blogs/security/how-to-add-dns-filtering-to-your-nat-instance-with-squid/)

This CDK application includes:

 * VPC with 2 public and 2 private subnets  cross 2 availability zones
 * An Auto-Scaling group with a Squid proxy instance in the public subnet in each availability zone
 * CloudWatch Metrics and Alarms, SNS Topic and Lambda to ensure availability of outbound connectivity to private instances
 * A Test instance to test outbound connectivity

## Preparing context variables
The `cdk.json` file requires the following values:

 * `account`:    The AWS account number to deploy the stacks
 * `region`:     The AWS region to deploy the stacks
 * `vpc_cidr`:   The CIDR range to use for the VPC

## Deploying the CDK app
1. `cdk bootstrap`              Initalise assets before deploy
2. `cdk synth`                  Emit the synthesized CloudFormation template
3. `cdk deploy "*"`             Deply all stacks to your AWS account & region  
   When prompted, approve the request to allow CloudFormation to create IAM roles and security groups (Answer *y* to the question: *Do you wish to deploy these changes?*)  

## Testing the solution
1. On the [AWS Systems Manager console](https://console.aws.amazon.com/systems-manager/): Choose **Session Manager**
2. Select the *test instance* and choose **Start Session**
3. After the connection is made, you can test the solution with the following commands. Only the last 2 requests should return a valid response, because Squid allows traffic to `*.amazonaws.com` only.
   1. `curl http://www.amazon.com`
   2. `curl https://www.amazon.com`
   3. `curl http://calculator.s3.amazonaws.com/index.html`
   4. `curl https://calculator.s3.amazonaws.com/index.html`

## General CDK help
This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the .env
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```