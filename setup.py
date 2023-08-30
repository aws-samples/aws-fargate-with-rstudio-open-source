import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="asg_custom_metric",
    version="0.0.1",
    description="CDK Python app for EC2 Auto Scalling with CloudWatch custom metric",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="author",
    package_dir={"": "asg_custom_metric"},
    packages=setuptools.find_packages(where="asg_custom_metric"),
    install_requires=[
        "aws-cdk-lib==2.92.0",
        "cdk-nag>=2.10.0",
        "constructs>=10.0.0,<11.0.0",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
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
