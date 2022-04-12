Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Automated AWS Route53 Cross-Account Hosted Zone Delegation

This project delivers infrastructure code to share Amazon Route 53 domains across AWS accounts by delegating a public domain from a central networking account to other accounts where applications can consume the domain by creating application service-specific subdomains.

## Solution Architecture

The following diagram depicts the overall solution architecture of the project.

<img src="/images/route53_zone_delegation.png" alt="Route 53 Zone Delegation Architecture on AWS"/>

Figure 1: Route 53 zone Delegation Automation Architecture

Numbered items refer to Figure 1.

1.	We used AWS Cloud Development Kit (AWS CDK) for Python to develop the infrastructure code and stored the code in an AWS CodeCommit repository.
2.	AWS CodePipeline integrates the AWS CDK stacks for automated builds into the central networking account and the consumer application account.
3.	The central networking accounts hosts the top level domain (e.g., amazon.com) for your organisation along with the subdomain (build.amazon.com) that you want to delegate to other accounts.
4.	Delegated hosted zone information is saved into AWS Systems Manager (SSM) Parameter Store for cross-account retrieval.
5.	The AWS Lambda function in the application ingress account retrieves the parent level hosted zone information from the central networking account SSM Parameter Store by assuming an AWS Identity and Access Management (IAM) role that has the necessary read access.
6.	You can now create the application-specific subdomains (e.g., dev.build.amazon.com, test.build.amazon.com) in Route 53 of the consumer application account.
7.	Apply certificates issued by AWS Certificate Manager on the subdomains you create.

## Deployment With AWS CodePipeline

Using the AWS Console you can create a public hosted zone (e.g., amazon.com) in Route 53 which will then be delegated to other accounts via subdomains (e.g., build.amazon.com). The hosted zone delegation needs to be automated using infrastructure as code as you might need to add more subdomains to the top level domain for delegation as you migrate and give cross-account access to the delegated zones to build applications in the cloud. For this automation to work, SSM Parameter store saves the hosted zone information and IAM roles are given read access to SSM for cross-account hosted zone retrieval.

The CDK stacks use a lambda function to retrieve the delegated subdomain hosted zone information. It then creates application specific subdomains in the consumer application account and applies certificates issued by Amazon Certificate Manager on the custom subdomains.

The development resources (AWS CodeCommit for hosting the AWS CDK in Python code, AWS CodePipeline for deployment of services) are created in a central AWS account. From this account, AWS CodePipeline deploys the automated code to a central networking account and the consumer application accounts.

It is assumed that AWS Shield or AWS Shield Advanced is already configured for the networking account, Amazon GuardDuty is enabled in all accounts along with AWS Config and AWS CloudTrail for monitoring and alerting on security events before deploying the infrastructure code. 

## Prerequisites

To deploy the CDK stacks, you should have the following prerequisites: 

1. Access to 3 AWS accounts (https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Fportal.aws.amazon.com%2Fbilling%2Fsignup%2Fresume&client_id=signup) (minimum 2) for a basic multi-account deployment. Ensure you have admin permissions access to each account. Typically, the following accounts are required:

    i. Central Development account - this is the account where the CodeCommit repository, ECR repositories, and CodePipeline will be created.

    ii. Central Network account - the Route53 base public domain will be hosted in this account

    iii. Consumer application account - account where application-specific subdomains will be created for applications to consume.

2. Permission to deploy all AWS services mentioned in the solution overview
3. Basic knowledge of Linux, AWS Developer Tools (AWS CDK in Python, CodePipeline, CodeCommit), AWS CLI and AWS services mentioned in the solution overview
4. Review the readmes delivered with the code  and ensure you understand how the parameters in cdk.json control the deployment and how to prepare your environment to deploy the CDK stacks via the pipeline detailed below.
5. Install (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) AWS CLI and create (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) AWS CLI profile for each account (pipeline, rstudio, network, datalake ) so that AWS CDK can be used.

    You can use the commands below to install AWS CLI version2 on Amazon Linux 2:

    ```
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    ```
6. Install the pre-requisites (https://docs.aws.amazon.com/cdk/latest/guide/work-with.html#work-with-prerequisites) for AWS CDK. You can install Node.js version 16 with the commands below on Amazon Linux 2:

    ```
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash  
    nvm install 16
    ```
    Run the below command with approproate version that will be prompted on your terminal

    ```
    nvm use --delete-prefix v16.12.0
    ```

    Install Python 3.6 or later following AWS CDK (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html) in Python:

    On Amazon Linux2, you can use the commands below to install Python3 and pip:

    ```
    sudo yum install python37
    curl -O https://bootstrap.pypa.io/get-pip.py
    python3 get-pip.py --user
    ```
    Add the executable path, `~/.local/bin`, to your PATH variable and run the commands below:

    ```
    python3 -m ensurepip --upgrade
    python3 -m pip install --upgrade pip
    python3 -m pip install --upgrade virtualenv
    ```
    Install the AWS CDK Toolkit (the cdk command) using the command below:

    ```
    npm install -g aws-cdk
    ```
7. Install (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html) AWS CDK in Python and bootstrap each account and allow the Central          Development account to perform cross-account deployment to all the other accounts.

        export CDK_NEW_BOOTSTRAP=1
        npx cdk bootstrap --profile <AWS CLI profile of central development account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://<Central Development Account>/<Region>

        npx cdk bootstrap \
        --profile <AWS CLI profile of cosumer application account> \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<RStudio Deployment Account>/<Region>

        npx cdk bootstrap \
        --profile <AWS CLI profile of central network account> \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<Central Network Account>/<Region>

## Installation

1. Clone the GitHub repository, check out the zone-delegate branch, and move into the aws-fargate-with-rstudio-open-source folder.

    ```
    git clone -b zone-delegate https://github.com/aws-samples/aws-fargate-with-rstudio-open-source.git
    ``` 

2. Setup your AWS CDK environment
 
    This project is set up like a standard Python project.  The initialization process also creates a virtualenv within this project, stored under the `.venv` directory.  To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

	To manually create a virtualenv on MacOS and Linux:

	```
	$ python3 -m venv .venv
	```

	After the init process completes and the virtualenv is created, you can use the following
	step to activate your virtualenv.

	```
	$ source .venv/bin/activate
	```

	If you are a Windows platform, you would activate the virtualenv like this:

	```
	% .venv\Scripts\activate.bat
	```

	Once the virtualenv is activated, you can install the required dependencies.

	```
	$ python3 -m pip install -r requirements.txt
	```  

	To add any additional dependencies, for example other CDK libraries, just add them to your `setup.py` file and rerun the `python3 -m pip install -r requirements.txt` command.

3. Create a CodeCommit repository (e.g., zone_delegation) to hold the source code for installation 

    ```
    aws codecommit --profile <profile of AWS account> create-repository --repository-name <name of repository>
    ```
4.   Configure the `cdk.json` to pass parameters for the build as per below:

     "instance": "dev" -- enter a name for your deployment instance or accept default. Your application URLs will be formed with this value as a subdomain. Remember not to use the same instance name twice even if the deployment is done in different accounts.

     "app_account_id": "xxxxxxxxxxxx" -- enter the AWS accounts where subdomains will be delegated for consumer application accounts  

     "network_account_id": "nnnnnnnnnnnn" -- provide the central network account where the base public route 53 domain resides. A subdomain created from this domain will be delegated to the consumer application accounts for configuring application-specific subdomains

     "code_repo_name": "codecommit_repository_name" -- enter the repository name you creaated in step 2 above.
    
     "r53_base_domain": "example.com" -- enter the publicly resolvable route53 domain from which subdomains will be derived. From this base public domain public hosted zones will be created by the stacks. This domain must exist in the route 53 public hosted zone of the AWS account.

    "r53_sub_domain": "build" -- enter the subdomain that will be created form the top level domain

     "sns_email_id": "abc@example.com" -- provide the email to use for sns notifications for this pipeline. 

     Apart from the parameters mentioned above, there are a few other parameters in cdk.json that are configured by default. Do not modify values of these parameters:

            "@aws-cdk/core:enableStackNameDuplicates"
            "aws-cdk:enableDiffNoFail"
            "@aws-cdk/core:stackRelativeExports"
            "@aws-cdk/aws-ecr-assets:dockerIgnoreSupport"
            "@aws-cdk/aws-secretsmanager:parseOwnedSecretName"
            "@aws-cdk/aws-kms:defaultKeyPolicies"
            "@aws-cdk/core:newStyleStackSynthesis"
   

5. At this point you can now synthesize and deploy the stacks for this application. Syntheisze the stacks before committing the code into CodeCommit repository you created. The reason behind this is to ensure all the necessary context values are populated into cdk.context.json file and to avoid the DUMMY values being mapped. 

```
cdk synth --profile <AWS CLI profile of the central development account>
cdk synth --profile <AWS CLI profile of the central network account>
cdk synth --profile <AWS CLI profile of the consumer application account>
```

6. Obtain the clone https URL of the AWS CodeCommit repository you created:

```
https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
```
        
Link your local codebase with the upstream CodeCommit repository using commands below:

``` 
$ git init   
$ git config --global credential.helper '!aws --profile <profile of the AWS account> codecommit credential-helper $@'
$ git remote add origin https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
```
        
Commit your code into the CodeCommit repository.

```   
$ git add .
$ git commit -am "R53 zone delegation initial commit"
$ git push --set-upstream origin master
```
        
7. Deploy the CDK stacks using AWS CodePipeline.This step will take around 15 minutes. This application is using the CdkPipeline construct - you simply deploy the CDK application and the rest of the actions are peformed by the pipeline.

```
cdk deploy --profile <AWS CLI profile of the central development account>
```

8. Log into AWS console and navigate to CodePipeline service. Monitor the pipeline and confirm the services build successfully. The pipeline name is `Rstudio-Shiny-<instance>`. From this point onwards the pipeline will be triggered on commits (git push) to the CodeCommit repository you created. There is no need to run cdk synth and cdk deploy anymore unless you change the `pipeline_stack.py` file.

9. Once the pipeline completes installation, you will be able to use the domain below where r53_base_domain, r53_sub_domain and instance are paramater values you passed into cdk.json. 

```         
<instance>.<r53_sub_domain>.<r53_base_domain>

```

## Deletions and Stack Ordering

1. From the consumer account using AWS CloudFormation console:

        a.      i. AppStage-Route53-Instance-<instance>

2. From the central network account using AWS CloudFormation console:

        b.      i.   R53Network-Route53Stack-<instance>

                ii.  R53Network-Network-Account-Resources-<instance>

                The above two stacks can be deleted in parallel

3. To delete the pipeline, use

```
cdk destroy --profile <AWS CLI profile of central development account>
```

or delete the `Zone-Delegation-Pipeline-Stack-<instance>` stack from AWS CloudFormation of central development account using AWS console of the AWS account.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

