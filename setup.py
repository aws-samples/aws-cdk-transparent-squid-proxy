import setuptools


with open("README.md", encoding="utf8", errors='ignore') as fp:
    long_description = fp.read()


setuptools.setup(
    name="squid_app",
    version="0.0.1",

    description="CDK Python application to deploy a Squid proxy in VPC",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "squid_app"},
    packages=setuptools.find_packages(where="squid_app"),

    install_requires=[
        "aws-cdk.core",
        "aws_cdk.aws_s3",
        "aws_cdk.aws_s3_deployment",
        "aws_cdk.aws_ec2",
        "aws_cdk.aws_autoscaling",
        "aws_cdk.aws_autoscaling_hooktargets",
        "aws_cdk.aws_iam",
        "aws_cdk.aws_lambda",
        "aws_cdk.aws_cloudwatch",
        "aws_cdk.aws_cloudwatch_actions",
        "aws_cdk.aws_sns",
        "aws_cdk.aws_sns_subscriptions"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)