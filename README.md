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

# RStudio Connect (RSC) and RStudio Package Manager (RSPM) project on AWS

This is a CDK application to deploy the AWS infrastructure required for RStudio Connect (RSC) and RStudio Package Manager using Serverless Architecture and AWS ECS.

**WARNING!** Deploying this projet will create AWS resources. Make sure you are aware of the costs and be sure to destory the stack when you are done by running `cdk destory`

This package depends on and may incorporate or retrieve a number of third-party
software packages (such as open source packages) at install-time or build-time
or run-time ("External Dependencies"). The External Dependencies are subject to
license terms that you must accept in order to use this package. If you do not
accept all of the applicable license terms, you should not use this package. We
recommend that you consult your company's open source approval policy before
proceeding.

Provided below is a list of External Dependencies and the applicable license
identification as indicated by the documentation associated with the External
Dependencies as of Amazon's most recent review.

THIS INFORMATION IS PROVIDED FOR CONVENIENCE ONLY. AMAZON DOES NOT PROMISE THAT
THE LIST OR THE APPLICABLE TERMS AND CONDITIONS ARE COMPLETE, ACCURATE, OR
UP-TO-DATE, AND AMAZON WILL HAVE NO LIABILITY FOR ANY INACCURACIES. YOU SHOULD
CONSULT THE DOWNLOAD SITES FOR THE EXTERNAL DEPENDENCIES FOR THE MOST COMPLETE
AND UP-TO-DATE LICENSING INFORMATION.

YOUR USE OF THE EXTERNAL DEPENDENCIES IS AT YOUR SOLE RISK. IN NO EVENT WILL
AMAZON BE LIABLE FOR ANY DAMAGES, INCLUDING WITHOUT LIMITATION ANY DIRECT,
INDIRECT, CONSEQUENTIAL, SPECIAL, INCIDENTAL, OR PUNITIVE DAMAGES (INCLUDING
FOR ANY LOSS OF GOODWILL, BUSINESS INTERRUPTION, LOST PROFITS OR DATA, OR
COMPUTER FAILURE OR MALFUNCTION) ARISING FROM OR RELATING TO THE EXTERNAL
DEPENDENCIES, HOWEVER CAUSED AND REGARDLESS OF THE THEORY OF LIABILITY, EVEN
IF AMAZON HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. THESE LIMITATIONS
AND DISCLAIMERS APPLY EXCEPT TO THE EXTENT PROHIBITED BY APPLICABLE LAW.

RStudio Connect - https://www.rstudio.com/products/connect
RStudio Package Manager - https://www.rstudio.com/products/package-manager/

---

## Solution Architecture

The solution architecture is based on professional versions of RStudio Connect and RStudio Package Manager docker containers. RStudio Connect and RStudio Package Manager services are configured across two Availability Zones (AZ) (https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html) for high availability. Both RStudio Connect and RStudio Package Manager containers support automatic scaling to handle incoming traffic depending on incoming number of requests, memory and CPU usage within the containers. 

Container images are stored and fetched from Amazon Elastic Container Registry (ECR) (https://aws.amazon.com/ecr/) with vulnerability scan enabled. Vulnerability issues should be addressed before deploying the images. 


<img src="/images/RSC-RSPM.png" alt="RStudio Connect and RStudio Package Manager Architecture on AWS"/>

Figure 1. RStudio Connect and RStudio Package Manager Architecture on AWS

Numbered items refer to Figure 1.

1. R users access RStudio Connect and RStudio Package Manager via Amazon Route 53 (https://aws.amazon.com/route53/). Route 53 is a DNS service for incoming requests.
2. Route 53 resolves incoming requests and forwards those onto AWS WAF (Web Application Firewall) (https://aws.amazon.com/waf) for security checks.
3. Valid requests reach an Amazon Application Load Balancer (ALB) (https://aws.amazon.com/elasticloadbalancing/application-load-balancer/) which forwards these to the ECS cluster. ALB checks incoming requests for HTTPS certificate, which is issued and validated by AWS Certificate Manager (https://aws.amazon.com/certificate-manager/).
4. The Amazon Elastic Containers Service (ECS) (https://aws.amazon.com/ecs) controls the containers in a cluster of EC2 instances (EC2 launch type) in an Auto-Scaling Group (https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html) (ASG) and is responsible for scaling up and down the number of containers as needed using Amazon ECS Capacity Provider (https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html). 
5. Incoming requests are processed by RStudio Connect server on any of the available RStudio Connect container; users are authenticated and applications are rendered on the web browser. RStudio Package Manager requests are routed to the Package Manager container.
6. Amazon Aurora Serverless (https://aws.amazon.com/rds/aurora/serverless/) PostgreSQL databases are used to provide High Availability utilizing multiple containers for both RStudio Connect and RStudio Package Manager. Amazon Aurora backs up the serverless cluster databases automatically. Data on Aurora is encrypted at rest using AWS Key Management Service (KMS) (https://aws.amazon.com/kms/).
7. Amazon Elastic File System (https://aws.amazon.com/efs/) (EFS) provides the persistent file system required by RStudio Connect and RStudio Package Manager. Data on EFS is encrypted at rest using AWS KMS. Amazon EFS is an NFS file system that stores data in multiple Availability Zones in an AWS Region (https://aws.amazon.com/about-aws/global-infrastructure/regions_az/) for data durability and high availability. Files created on the RStudio Connect and RStudio Package Manager container EFS mounts will be automatically backed up by EFS.
8. If the user session communicates with public internet, outbound requests are sent to a NAT Gateway (https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) from the private container subnet.
9. NAT Gateway sends outbound requests to be processed via an Internet Gateway (https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html). Route to internet can also be configured by AWS Transit Gateway. (https://aws.amazon.com/transit-gateway)

We use AWS Cloud Development Kit (https://aws.amazon.com/cdk) (AWS CDK) for Python to develop the infrastructure code and store the code in an AWS CodeCommit (https://aws.amazon.com/codecommit/) repository, so that AWS CodePipeline (https://aws.amazon.com/codepipeline/) can integrate the AWS CDK stacks for automated builds. 

The deployment code utilizes Route 53 Public hosted zones to service the RStudio Connect and RStudio Package Manager on publicly accessible URLs. You can use Route53 Private Hosted Zones (https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zones-private.html) for the RStudio Connect and RStudio Package Manager containers with an internal ALB which will provide private endpoints for users coming from RStudio on SageMaker in a VPC-only connectivity mode. This means you will not need a public domain to pre-exist in your AWS account. You will however, need to fetch the public docker images (RStudio Connect (https://hub.docker.com/r/rstudio/rstudio-connect), RStudio Package Manager (https://hub.docker.com/r/rstudio/rstudio-package-manager)) and store those in a private ECR repository and point the deployment code to those images for the infrastructure build.  

If all communications amongst AWS services must stay within AWS, you can use AWS PrivateLink (https://aws.amazon.com/privatelink) to configure VPC endpoints for AWS services. PrivateLink makes sure that inter-service traffic is not exposed to the internet for AWS service endpoints. 

It is assumed that AWS Shield or AWS Shield Advanced is already configured for the networking account, Amazon GuardDuty is enabled in all accounts along with AWS Config and AWS CloudTrail for monitoring and alerting on security events before deploying the infrastructure code. It is recommended that you use an egress filter for network traffic destined for the internet. The configuration of egress filter is not in scope for this codebase.

All services in this deployment are meant to be in one particular AWS region. The AWS services used in this architecture are managed services and configured for high availability. As soon as a service becomes unavailable, the service will automatically be brought up in the same Availability Zone (AZ) or in a different AZ within the same AWS Region. 

### Prerequisites:

* To deploy the CDK stacks from the source code, you should have the following prerequisites:

1. AWS Identity and Access Management (https://aws.amazon.com/iam/) (IAM) permissions to deploy all AWS services mentioned in the solution overview.

2. Obtain RStudio Connect and RStudio Package Manager Licensing and the activation keys.

3. Basic knowledge of R, RStudio Connect, RStudio Package Manager, Linux, AWS Developer Tools (AWS CDK in Python, AWS CodePipeline, AWS CodeCommit), AWS CLI and, the AWS services mentioned in the solution overview.

4. Ensure you have a publicly resolvable domain/subdomain in your AWS account as a public hosted zone (https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/CreatingHostedZone.html) in Amazon Route 53. This domain will need be passed as parameter to the CDK stacks to create RStudio Connect/RStudio Package Manager URLs. 

5. Review the readmes delivered with the code and ensure you understand how the parameters in cdk.json control the deployment and how to prepare your environment to deploy the cdk stacks via the pipeline detailed below.

6. Install AWS CLI (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) and create an AWS CLI profile (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) for your AWS  account so that AWS CDK can be used.

    You can use the commands below to install AWS CLI version2 on Amazon Linux 2:

    ```
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    ```

7. Install the pre-requisites (https://docs.aws.amazon.com/cdk/latest/guide/work-with.html#work-with-prerequisites) for AWS CDK. You can install Node.js version 16 with the commands below on Amazon Linux 2:

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

8. Bootstrap the AWS account to be used for installation of RSC/RSPM. You can use the default arn:aws:iam::aws:policy/AdministratorAccess to use all types of services required for this deployment but the preferred option is to use an AWS IAM Policy (https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) that only provides access to the services you need.

    ```
    export CDK_NEW_BOOTSTRAP=1 
    npx cdk bootstrap --profile <AWS CLI profile of the account> \
    --cloudformation-execution-policies <AWS Policy ARN> \
    aws://<Account>/<Region>
    ```

9. Ensure you have a Docker hub login account, otherwise you might get an error while pulling the container images from Docker Hub with the pipeline – You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits.Using the AWS CLI – Create a secret to store your DockerHub credentials as follows. Do not change the value in --name field.

    ```
    aws secretsmanager --profile <AWS CLI profile of the account> create-secret  \
    --name ImportedDockerId \
    --secret-string '{"username":"<dockerhub username>", "password":"<dockerhub password>"}'
    ```

10. Create secrets to store RSC and RSPM license keys. Do not change the values in --name fields.

    ```
    aws secretsmanager --profile <AWS CLI profile of the account> create-secret --name RSCLicenseKey --secret-string "<RSC license key>"

    aws secretsmanager --profile <AWS CLI profile of the account> create-secret --name RSPMLicenseKey --secret-string "<RSPM license key>"
    ```

### Installation Steps:

1. Clone the GitHub repository, check out the rsc-rspm branch, and move into the aws-fargate-with-rstudio-open-source folder.

    ```
    git clone -b rsc-rspm https://github.com/aws-samples/aws-fargate-with-rstudio-open-source.git
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

3. Create a CodeCommit repository (e.g., rsc_rspm) to hold the source code for installation of RStudio Connect/RStudio Package Manager 

    ```
    aws codecommit --profile <profile of AWS account> create-repository --repository-name <name of repository>

    ```

4.   Configure the `cdk.json` to pass parameters for the build as per below:

     "instance": "dev" -- enter a name for your RSC/RSPM instance or accept default. The RSC/RSPM URLs will be formed with this value as a subdomain. Remember not to use the same instance name twice even if the deployment is done in different accounts.
    
     "r53_base_domain": "example.com" -- enter the publicly resolvable route53 domain from which subdomains for RSC/RSPM will be derived. From this base public domain RSC/RSPM public hosted zones will be created by the stacks. This domain must exist in the route 53 public hosted zone of the AWS account.

     "code_repo_name": "codecommit_repository_name" -- enter the repository name you creaated in step 2 above.

     "vpc_cidr_range": "10.8.0.0/16" -- provide the VPC CIDR range for your deployemnts in the rstudio deployment accounts or accept default. If the VPC CIDR already exists, it will be used by the installation

     "ec2_instance_type": "t3.xlarge" -- provide the EC2 instance type for the ECS cluster or accept default

     "allowed_ips" : "xxx.xxx.xxx.xxx/28, yyy.yyy.yyy.yyy/28", -- provide the IP ranges that will be whitelisted in the AWS WAF for accessing RSC/RSPM. If no IPs are provided, RSC/RSPM URLs will be accessible from all IPs.

     "sns_email_id": "abc@example.com" -- provide the email to use for sns notifications for this pipeline. 

     Apart from the parameters mentioned above, there are a few other parameters in cdk.json that are configured by default. Do not modify values of these parameters:

            "@aws-cdk/core:enableStackNameDuplicates"
            "aws-cdk:enableDiffNoFail"
            "@aws-cdk/core:stackRelativeExports"
            "@aws-cdk/aws-ecr-assets:dockerIgnoreSupport"
            "@aws-cdk/aws-secretsmanager:parseOwnedSecretName"
            "@aws-cdk/aws-kms:defaultKeyPolicies"
            "@aws-cdk/core:newStyleStackSynthesis"
   
5. There are some configuration parameters in parameter.json. You do not need to modify these unless you want to change the container capacity values or the names of your secret parameters. Note that the number of containers you run for RSC/RSPM are dependent on the number of EC2 servers in the autoscaling group as well as the EC2 instance type you choose in cdk.json.

6. At this point you can now synthesize and deploy the stacks for this application. Syntheisze the stacks before committing the code into CodeCommit repository you created. The reason behind this is to ensure all the necessary context values are populated into cdk.context.json file and to avoid the DUMMY values being mapped. 

```
cdk synth --profile <AWS CLI profile of the account>
```

7. Obtain the clone https URL of the AWS CodeCommit repository you created:

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
$ git commit -am "RSC/RSPM initial commit"
$ git push --set-upstream origin master
```
        
8. Deploy the CDK stacks to install RStudio Connect/RStudio Package Manager using AWS CodePipeline.This step will take around 30 minutes. This application is using the CdkPipeline construct - you simply deploy the CDK application and the rest of the actions are peformed by the pipeline.

```
cdk deploy --profile <AWS CLI profile of the account>
```

9. Log into AWS console and navigate to CodePipeline service. Monitor the pipeline and confirm the services build successfully. The pipeline name is `RStudio-Connect-PM-App-Pipeline-<instance>`. From this point onwards the pipeline will be triggered on commits (git push) to the CodeCommit repository you created. There is no need to run cdk synth and cdk deploy anymore.

10. Once the pipeline completes installation, you will be able to access RStudio Connect and RStudio Package Manager using the following URLs respectively where r53_base_domain and instance are paramater values you passed into cdk.json :

```         
1. https://connect.<instance>.<r53_base_domain>
2. https://package.<instance>.<r53_base_domain>
```

## Deletions and Stack Ordering

Please bear in mind that if you have already deployed the pipeline and created RSC/RSPM instances, you should not attempt to deploy an instance with the same name used for an already deployed instance even if it is in a different AWS account. This is because RSC/RSPM URLs depend on the instance name to make it unique.

In case you need to delete the stacks for an instance, please follow the following order of deletion. Note that although EFS mounts are persistent and live through container restarts unless the EFS stack itself is deleted. Although all EFS mountpoints are enabled for backup, you should check and verify that backups serve your purpose. The Aurora serverless cluster databases are automatically backed up and if the aurora stacks are deleted, a backup is taken before stack deletion.

1. From the AWS account where you deployed RSC/RSPM, using AWS CloudFormation console:

        a.      i.   RSCRSPMStage-Waf-RSC-<instance>

                ii.  RSCRSPMStage-Waf-RSPM-<instance>

                The avove two stacks can be deleted in parallel.

        b.      i.   RSCRSPMStage-EC2-RSC-<instance>

                ii.  RSCRSPMStage-EC2-RSPM-<instance>

                The above two stacks can be deleted in parallel

        c.      i.   RSCRSPMStage-Efs-RSC-<instance>

                ii.  RSCRSPMStage-Efs-RSPM-<instance>

                iii. RSCRSPMStage-RdsDb-RSC-<instance>

                iv.  RSCRSPMStage-RdsDb-RSPM-<instance>

                v.   RSCRSPMStage-Ecs-RSC-RSPM-<inConstance>

                vi.  RSCRSPMStage-r53-RSC-RSPM-<instance>

                The above six stacks can be deleted in parallel

        d.      i.   RSCRSPMStage-Kms-RSC-RSPM-<instance>

                ii.  RSCRSPMStage-VPC-RSC-RSPM-<instance>

                The above two stacks can be deleted in parallel

4. Delete secrets from AWS Secrets Manager for the instance. You can use AWS CLI for this by running a command like below. --force-delete-without-recovery removes the secret instantaneously. You can also run a shell script to delete all the secrets for the instance.

```
aws secretsmanager --profile <AWS CLI profile of the account> delete-secret --secret-id <secret id>  --force-delete-without-recovery

```

6. To delete the pipeline, use 

```
cdk destroy --profile <AWS CLI profile of the account> 

```

or delete the `RSCRSPM-<instance>` stack from AWS CloudFormation using AWS console of the AWS account.

## Some useful CDK commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Notes on using Amazon ECS Exec

You can use Amazon ECS Exec (https://aws.amazon.com/blogs/containers/new-using-amazon-ecs-exec-access-your-containers-fargate-ec2/) to access the RSC/RSPM containers. It is a preferred secure way to access containers on AWS ECS. The RSC/RSPM containers are configured with Amazon ECS Exec.

Using the AWS CLI with SSM plugin installed, you can login to the containers with the commands below. `<instance>` is the value for instance parameter you passed in cdk.json.

```
export AWS_PROFILE=<profile name>
export AWS_REGION=<region name>
```
Get the task id of the container you want to login to from the task arn output using command below. The task id is the lst field of the task arn after the forward slash.

```
aws ecs --profile $AWS_PROFILE list-tasks --cluster RSC-RSPM-ecs-cluster-<instance>
```
With the task arn from command above, find the container name from the output of the command below. Container name will be either `RSC-ec2-<instance>` or `RSPM-ec2-<instance>`

```
aws ecs --profile $AWS_PROFILE describe-tasks --tasks "<task_arn>" --cluster RSC-RSPM-ecs-cluster-<instance>
```
Start an ECS exec session for RSC task:

```
aws ecs --profile $AWS_PROFILE execute-command  \
    --region $AWS_REGION \
    --cluster RSC-RSPM-ecs-cluster-<instance> \
    --task <task id> \
    --container RSC-ec2-<instance> \
    --command "/bin/bash" \
    --interactive
```
For RSPM:

```
aws ecs --profile $AWS_PROFILE execute-command  \
    --region $AWS_REGION \
    --cluster RSC-RSPM-ecs-cluster-<instance> \
    --task <task id> \
    --container RSPM-ec2-<instance> \
    --command "/bin/bash" \
    --interactive
```

## Security

See CONTRIBUTING.md

## License

This library is licensed under the MIT-0 License. See the LICENSE file.