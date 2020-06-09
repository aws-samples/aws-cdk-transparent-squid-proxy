#!/usr/bin/env python3

from aws_cdk import core

from squid_app.vpc_stack import VPCStack
from squid_app.squid_stack import SquidStack
from squid_app.test_instance_stack import TestInstanceStack

app = core.App()

# Get context variable values 
account = app.node.try_get_context('account')
region = app.node.try_get_context('region')
vpc_cidr = app.node.try_get_context('vpc_cidr')

# Set the env context variable to use the appropriate account and region
env = core.Environment(account=account, region=region)

# Create the VPC stack using the context values 
vpc_stack = VPCStack(app, "vpc", env=env, vpc_cidr=vpc_cidr)

# Create the squid stack in the VPC
SquidStack(app, "squid", env=env, vpc=vpc_stack.vpc)

# Create the stack that deploys a test instance
TestInstanceStack(app, "test-instance", env=env, vpc=vpc_stack.vpc)

app.synth()