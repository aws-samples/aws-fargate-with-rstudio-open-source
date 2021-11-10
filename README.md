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

RStudio Server Open Source Edition - https://www.rstudio.com/products/rstudio - AGPL-3.0
Shiny Server Open Source Edition - https://www.rstudio.com/products/shiny/shiny-server - AGPL-3.0

---

## Open Source RStudio/Shiny on AWS Fargate

This project delivers infrastructure code to run a scalable and highly available RStudio and Shiny Server installation on AWS utilizing various AWS services like Fargate, ECS, EFS, DataSync, S3 etc. 

## Solution Architecture

The following diagram depicts the overall solution architecture of the project.

<img src="/images/Rstudio_architecture.png" alt="Rstudio/Shiney Open Source Architecture on AWS"/>

Figure 1. RStudio/Shiny Open Source Architecture on AWS

Numbered items refer to Figure 1.

1. R users access RStudio Server and Shiny App via Amazon Route 53. Route 53 is a DNS service for incoming requests.
2. Route 53 resolves incoming requests and forwards those onto AWS WAF (Web Application Firewall) for security checks.
3. Valid requests reach an Amazon Application Load Balancer (ALB) which forwards these to the Amazon Elastic Containers Service (ECS) cluster.
4. The cluster service controls the containers and is responsible for scaling up and down the number of instances as needed.
5. Incoming requests are processed by RStudio server; users are authenticated and R sessions are spawned for valid requests. Shiny users are routed to the Shiny container.
6. If the R session communicates with public internet, outbound requests can be filtered via a proxy server and then sent to a NAT Gateway.
7. NAT Gateway sends outbound requests to be processed via an Internet Gateway. Route to internet can also be configured by AWS Transit Gateway.
8. The R users require data files to be transported onto the container. To facilitate this, files are transferred to Amazon Simple Storage Service (S3) using AWS Transfer for SFTP or S3 upload.
9. The uploaded files from S3 are synced to Amazon Elastic File System (EFS) by AWS DataSync.
10. Amazon EFS provides the persistent file system required by RStudio server. Data scientists can deploy Shiny apps from their RStudio Server container to the Shiny Server container easily by the shared file system.
11. RStudio can be integrated with S3 and R sessions can query Amazon Athena tables built on S3 data using a JDBC connection. Athena is a serverless interactive query service that analyses data in Amazon S3 using standard SQL.

You can use Amazon ECS Exec to log in to both RStudio Open Source and Shiny containers.

## Deployment With AWS CodePipeline

The development resources for the RStudio/Shiny deployment (AWS CodeCommit for hosting the AWS CDK in Python code, AWS CodePipeline for deployment of services, Amazon ECR repository for container images) are created in a central AWS account. From this account, AWS Fargate services for RStudio and Shiny along with the integrated services like Amazon ECS, Amazon EFS, AWS DataSync, AWS KMS, AWS WAF, Amazon ALB, and Amazon VPC constructs like Internet Gateway, NAT gateway, Security Groups etc are deployed into another AWS account. 

The RStudio/Shiny deployment accounts obtain the networking information for the publicly resolvable domain from a central networking account and the data feed for the containers come from a central data repository account. Users upload data to the S3 buckets in the central data account or configure an automated service like AWS Service for SFTP to programmatically upload files. The uploaded files are transferred to the containers using AWS DataSync and Amazon EFS. The RStudio/Shiny containers are integrated with Amazon Athena for directly interacting with tables built on top of S3 data in the central data account.

It is assumed that AWS Shield or AWS Shield Advanced is already configured for the networking account, Amazon GuardDuty is enabled in all accounts along with AWS Config and AWS CloudTrail for monitoring and alerting on security events before deploying the infrastructure code. It is recommended that you use an egress filter for network traffic destined for the internet. The configuration of egress filter is not in scope for this codebase.

All services in this deployment are meant to be in one particular AWS region. The AWS services used in this architecture are managed services and configured for high availability. As soon as a service becomes unavailable, the service will automatically be brought up in the same Availability Zone (AZ) or in a different AZ within the same AWS Region. The following diagram depicts the deployment architecture of Open SOurce Rstudio/Shiny on AWS.


<img src="/images/Rstudio_deployment_image.png" alt="Rstudio/Shiney Open Source Architecture on AWS"/>

Figure 2. RStudio/Shiny Open Source Deployment on AWS Serverless Infrastructure

## Deployment Architecture

The infrastructure code provided in this repository creates all resources described in the architecture above.

Numbered items refer to Figure 2.

1. The infrastructure code is developed using AWS CDK for Python and stored in an AWS CodeCommit repository. 
2. The CDK stacks are integrated into AWS CodePipeline for automated builds. The stacks are segregated into four different stages and are organised by AWS services.
3. The container images used in the build are fetched from public Docker Hub using AWS CodePipeline  and are stored into Amazon ECR repositories for cross-account access. These images are accessed by the pipeline to create the Fargate containers in the deployment accounts.
4. The build code uses a key from AWS Key Management Service (AWS KMS) to create secrets for RStudio front-end password in AWS Secrets Manager. 
5. The central networking account has the pre-configured base public domain. This is done outside the automated pipeline and the base domain info is passed on as a parameter in cdk.json
6. The base public domain will be delegated to the deployment accounts using AWS SSM Parameter Store.
7. An AWS Lambda function retrieves the delegated Route 53 zone for configuring the RStudio and Shiny sub-domains.
8. AWS Certificate Manager https certificates are applied on the RStudio and Shiny sub-domains
9. Amazon ECS cluster is created to control the RStudio/Shiny containers and to scale up and down the number of containers as needed.
10. RStudio container is configured for the instance in a private subnet. RStudio container is not horizontally scalable for the Open Source version of RStudio. You can create one RStudio container for each Data Scientist depending on your compute requirements. To create multiple RStudio containers for data scientists, you need to specify the number of rstudio containers you need in cdk.json. If your compute requirements exceed Fargate container compute limits, you can use the EC2 launch type of Amazon ECS which offers a range of EC2 servers to fit your compute requirement. The code delivered with this blog caters for EC2 launch types as well controlled by the installation type paramter in cdk.json. For EC2 launch type, the autoscaling group is configured with multiple EC2 servers and an Amazon ECS capacity provider.
11. Shiny containers will be configured in the private subnet to be horizontally scalable. Shiny containers are configured to scale depending on number of requests, memory and CPU usage.
12. Application Load Balancers are registered with RStudio and Shiny services for routing traffic to the containers and to perform health checks.
13. AWS WAF rules are built to provide additional security to RStudio and Shiny endpoints. You can specify whitelisted IPs in the WAF stack to restrict access to RStudio and Shiny from only allowed IPs.
14. Users will upload files to be analysed to a central data account either with manual S3 upload or programmatically using AWS Transfer for SFTP.
15. AWS DataSync will push files from Amazon S3 to cross-account Amazon EFS on an hourly interval schedule.
16. An AWS Lambda trigger will be configured to trigger DataSync transfer on demand outside of the hourly schedule for files that require urgent analysis. It is expected that bulk of the data transfer will happen on the hourly schedule and on demand trigger will only be used when necessary.
17. Amazon EFS file systems are attached to the containers for persistent storage. All containers will share the same file systems except the user home directories. This is to facilitate deployment of Shiny Apps from RStudio containers using shared file system and to access data uploaded in S3 buckets. These file systems will live through container recycles.
18. You can create Amazon Athena tables on the central data account S3 buckets for direct interaction using JDBC from RStudio container. Access keys for cross account operation will not be configured in the RStudio container R environment. It is recommended that you obtyain short term credential when interacting with AThena from RStudio and not store credentials in the containner. 


## Prerequisites

To deploy the CDK stacks, you should have the following prerequisites: 

1. Access to 4 AWS accounts (https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Fportal.aws.amazon.com%2Fbilling%2Fsignup%2Fresume&client_id=signup) (minimum 3) for a basic multi-account deployment. Ensure you have admin permissions access to each account. Typically, the following accounts are required:

    i. Central Development account - this is the account where the CodeCommit repository, ECR repositories, and CodePipeline will be created.

    ii. Central Network account - the Route53 base public domain will be hosted in this account

    iii. Rstudio instance account - account where RStudio and Shiny containers will be deployed for an instance (dev, test, uat, prod etc) along with associated services as described in the solution architecture.

    iv. Central Data account - this is the account to be used for deploying the data lake resources - such as S3 bucket for picking up ingested source files.

2. Permission to deploy all AWS services mentioned in the solution overview
3. Review RStudio and Shiny Open Source Licensing: AGPL v3 (https://www.gnu.org/licenses/agpl-3.0-standalone.html)
4. Basic knowledge of R, RStudio Server, Shiny Server, Linux, AWS Developer Tools (AWS CDK in Python, CodePipeline, CodeCommit), AWS CLI and AWS services mentioned in the solution overview
5. Review the readmes delivered with the code  and ensure you understand how the parameters in cdk.json control the deployment and how to prepare your environment to deploy the CDK stacks via the pipeline detailed below.
6. Install (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) AWS CLI and create (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) AWS CLI profile for each account (pipeline, rstudio, network, datalake ) so that AWS CDK can be used.

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
8. Install (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html) AWS CDK in Python and bootstrap each account and allow the Central          Development account to perform cross-account deployment to all the other accounts.

        export CDK_NEW_BOOTSTRAP=1
        npx cdk bootstrap --profile <AWS CLI profile of central development account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://<Central Development Account>/<Region>

        npx cdk bootstrap \
        --profile <AWS CLI profile of rstudio deployment account> \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<RStudio Deployment Account>/<Region>

        npx cdk bootstrap \
        --profile <AWS CLI profile of central network account> \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<Central Network Account>/<Region>

        npx cdk bootstrap \
        --profile <AWS CLI profile of central data account> \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<Central Data Account>/<Region>

9. Ensure you have a Docker hub login account, otherwise you might get an error while pulling the container images from Docker Hub with the pipeline – You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits.Using the AWS CLI – Create a secret to store your DockerHub credentials as follows. Do not change the value in --name field.

    ```
    aws secretsmanager --profile <AWS CLI profile of the account> create-secret  \
    --name ImportedDockerId \
    --secret-string '{"username":"<dockerhub username>", "password":"<dockerhub password>"}'


## Installation

1. Clone the GitHub repository, check out the main branch, and move into the aws-fargate-with-rstudio-open-source folder.

    ```
    git clone -b main https://github.com/aws-samples/aws-fargate-with-rstudio-open-source.git
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

3. Create a CodeCommit repository (e.g., rstudio_shiny) to hold the source code for installation of RStudio/Shiny 

    ```
    aws codecommit --profile <profile of AWS account> create-repository --repository-name <name of repository>
    ```
4.   Configure the `cdk.json` to pass parameters for the build as per below:

     "instance": "dev" -- enter a name for your RStudio/Shiny instance or accept default. The RStudio/Shiny URLs will be formed with this value as a subdomain. Remember not to use the same instance name twice even if the deployment is done in different accounts.

     "rstudio_account_id": "xxxxxxxxxxxx" -- enter the AWS accounts where the RStudio/Shiny will be deployed.  

     "rstudio_pipeline_account_id": "qqqqqqqqqqqqq" -- enter the account id of the central development account

     "network_account_id": "nnnnnnnnnnnn" -- provide the central network account where the base public route 53 domain resides. This domain will be delegated to the rstudio/shiny deployemnt accounts for configuring subdomains

     "datalake_account_id": "ttttttttttt" -- provide the account id which will be used by users or sftp process to push files to S3 in the central data account. Files uploaded to S3 in this account will be synced to the EFS on the rstudio/shiny container in the rstudio/shiny deployment accounts

     "code_repo_name": "codecommit_repository_name" -- enter the repository name you creaated in step 2 above.
    
     "r53_base_domain": "example.com" -- enter the publicly resolvable route53 domain from which subdomains for RStudio/Shiny will be derived. From this base public domain RStudio/Shiny public hosted zones will be created by the stacks. This domain must exist in the route 53 public hosted zone of the AWS account.

     "rstudio_install_types": "ec2" -- provide the ECS launch type(fargate/ec2) of your container for the rstudio container. This is to scale rstudio vertically as the open source rstudio does not allow running muliple containers on the same URL. Shiny will run multiple containers on Fargate and will scale horizontally. 

     "rstudio_ec2_instance_types": "t3.xlarge" -- provide the EC2 instance type for the ECS cluster if the rstudio container will run on EC2 launch type of ECS. Note that when you use EC2 launch type, use EC2 instance type with enough memory for the pipeline to place a new task in the conatiner instance during blue/green ecs deployment. Otherwise, the fargate stack build may fail and you will need to delete stacks up to the fargate stack before rerunning the pipeline.

     "rstudio_container_memory_in_gb": "8" -- provide the amount of memory for rstudio container for fargate launch type, the number of vCPUs will be derived from the amount of memory; note that a fargate container can go up to 30GB/4vCPU max

     "number_of_rstudio_containers": "4" -- provide the number of rstudio containers you want to spin up. These containers will run on different URLS and will share the same EFS file systems. This is to provide a mechanism for horizontal scaling of RStudio and to allow invidual containers for RStudio.

     "vpc_cidr_range": "10.8.0.0/16" -- provide the VPC CIDR range for your deployemnts in the rstudio deployment accounts or accept default. If the VPC CIDR already exists, it will be used by the installation

     "allowed_ips" : "xxx.xxx.xxx.xxx/28, yyy.yyy.yyy.yyy/28", -- provide the IP ranges that will be whitelisted in the AWS WAF for accessing RStudio/Shiny. If no IPs are provided, RStudio/Shiny URLs will be accessible from all IPs.

     "sns_email_id": "abc@example.com" -- provide the email to use for sns notifications for this pipeline. 

     Apart from the parameters mentioned above, there are a few other parameters in cdk.json that are configured by default. Do not modify values of these parameters:

            "@aws-cdk/core:enableStackNameDuplicates"
            "aws-cdk:enableDiffNoFail"
            "@aws-cdk/core:stackRelativeExports"
            "@aws-cdk/aws-ecr-assets:dockerIgnoreSupport"
            "@aws-cdk/aws-secretsmanager:parseOwnedSecretName"
            "@aws-cdk/aws-kms:defaultKeyPolicies"
            "@aws-cdk/core:newStyleStackSynthesis"
   
5. There are some configuration parameters in parameter.json. You do not need to modify these unless you want to change the container capacity values or the names of your arameters. Note that the number of containers you run for RStudio are dependent on the EC2 server memory/cpu for the EC2 instance type you choose in cdk.json.

6. Verify email in Amazon SES for the sns_email parameter value in cdk.json. You will get a verification email in the address provided. Click verify before proceeding with the next steps.

```
aws ses --profile <AWS CLI profile of the RStudio deployment account> verify-email-identity --email-address <sns_email in cdk.json>
```

7. At this point you can now synthesize and deploy the stacks for this application. Syntheisze the stacks before committing the code into CodeCommit repository you created. The reason behind this is to ensure all the necessary context values are populated into cdk.context.json file and to avoid the DUMMY values being mapped. 

```
cdk synth --profile <AWS CLI profile of the central development account>
cdk synth --profile <AWS CLI profile of the central network account>
cdk synth --profile <AWS CLi profile of the central data account>
cdk synth --profile <AWS CLI profile of the RStudio deployment account>
```

8. Obtain the clone https URL of the AWS CodeCommit repository you created:

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
$ git commit -am "RStudio/Shiny initial commit"
$ git push --set-upstream origin master
```
        
9. Deploy the CDK stacks to install RStudio Connect/RStudio Package Manager using AWS CodePipeline.This step will take around 30 minutes. This application is using the CdkPipeline construct - you simply deploy the CDK application and the rest of the actions are peformed by the pipeline.

```
cdk deploy --profile <AWS CLI profile of the central development account>
```

10. Log into AWS console and navigate to CodePipeline service. Monitor the pipeline and confirm the services build successfully. The pipeline name is `Rstudio-Shiny-<instance>`. From this point onwards the pipeline will be triggered on commits (git push) to the CodeCommit repository you created. There is no need to run cdk synth and cdk deploy anymore unless you change the `pipeline_stack.py` file.

11. Once the pipeline completes installation, you will be able to access RStudio and Shiny using the following URLs respectively where r53_base_domain, instance are paramater values you passed into cdk.json. `<number>` stands for the container number. If you specified a number greater than one for number_of rstudio_containers in cdk.json, you will receive a corresponding URL for each of those numbers. You will get an email with password and URL details at the address you specified in sns_email in cdk.json.

```         
1. https://container<number>.<instance>.build<instance>.<r53_base_domain>
2. https://shiny.<instance>.build<instance>.<r53_base_domain>
```

## Notes about the Deployment

2. For RStudio server, the default username is rstudio and the password is randomly generated and stored in AWS Secrets Manager. The rstudio user will have sudo access in the containers. 

3. To work with your dataset in RStudio, you will need to upload files in the S3 bucket in the Central Data account. There are two folders in the S3 bucket - one is for hourly scheduled file transfer and another is to trigger the data transfer as soon as the files arrive in the folder. These files are transferred to the EFS mounts ```(/s3_data_sync/hourly_sync and /s3_data_sync/instant_upload)``` which are mounted to all the RStudio and Shiny containers.

4. The RStudio and Shiny containers share a common EFS mount ```(/srv/shiny-server)``` for sharing shiny app files. From Rstudio, save your files in `/srv/shiny-server` to deploy Shiny apps.

5. RStudio containers are configured with a different persistent EFS mount for /home in each container. The Shiny containers share a similar /home EFS mount. Although the /home file systems are persistent, recreating the containers will delete /home file systems. You are encouraged to save your work eithe rin a Git repository or under your folder in `/srv/shiny-server`

6. Although EFS mounts are persistent and live through container restarts, when you delete the 
```RstudioShinyApp-Fargate-RstudioStack-<instance>``` or ```RstudioShinyApp-EC2-RstudioStack-<instance>``` stacks, the /home file systems in the containers also get deleted. This is to faciliate automatic stack updates when you change the cdk.json paramaters like rstudio_individual_containers or rstudio_install_types or rstudio_users. Save your work and files in the other EFS mounts in the container such as `/s3_data_sync/hourly_sync or /s3_data_sync/instant_upload/s3_instant_sync` locations before you recreate containers. You can also save files to a Git repository directly from the RStudio IDE.

7. Deleting ```RstudioShinyApp-Efs-RstudioStack-<instance>``` stack deletes the other EFS mounts mentioned above. Although all EFS mountpointa are enabled for backup, you should check and verify that backups server your purpose.

8. The WAF rules will allow connection to Rstudio and Shiny containers only from the IPs/IP ranges you specify in cdk.json. If you do not want to restrict any IP, do not provide any value against the parameter allowed_ips in cdk.json.

9. Note that when you use EC2 launch type, use EC2 instance type with enough memory for the pipeline to place a new task in the conatiner instance during blue/green ecs deployment. Otherwise, the stack build may fail and you will need to delete stacks before rerunning the pipeline.

10. You can use Amazon ECS Exec (https://aws.amazon.com/blogs/containers/new-using-amazon-ecs-exec-access-your-containers-fargate-ec2/) to access the RStudio/Shiny containers. It is a preferred secure way to access containers on AWS ECS. The RStudio/Shiny containers are configured with Amazon ECS Exec.


## Deletions and Stack Ordering

Please bear in mind that if you have already deployed the pipeline and created rstudio instances, you should not attempt to deploy an instance with the same instance name in another rstudio deployment account. This is because rstudio and shiny URLs depend on the instance name to make it unique.

In case you need to delete the stacks for an instance, please follow the following order of deletion. 

Note that although EFS mounts are persistent and live through container restarts, when you delete the 
`RstudioShinyApp-Fargate-RstudioStack-<instance>` or `RstudioShinyApp-EC2-RstudioStack-<instance>` stacks, the /home file systems in the containers also get deleted. This is to make sure each individual container gets a different /home mount. Save your work and files in the other EFS mounts in the container such as `/s3_data_sync/hourly_sync` or `/s3_data_sync/instant_upload/s3_instant_sync` locations before you recreate these stacks. 

Also note that deleting `RstudioShinyApp-Efs-RstudioStack-<instance>` stack deletes the other EFS mounts mentioned above. Although all EFS mountpointa are enabled for backup, you should check and verify that backups server your purpose.

1. From the rstudio deployment account using AWS CloudFormation console:

        a.      i.   RstudioShinyApp-Rstudio-SesEmailStack-<instance>

                ii.  RstudioShinyApp-Waf-RstudioStack-<instance>

                iii. RstudioShinyApp-Waf-ShinyStack-<instance>

                The avove three stacks can be deleted in parallel.

        b.      i.   RstudioShinyApp-RstudioEc2Stack-<instance> or RstudioShinyApp-RstudioFargateStack-<instance>

                ii.  RstudioShinyApp-Fargate-ShinyStack-<instance>

                iii, RstudioShinyApp-Datasync-RstudioStack-<instance>

                The above three stacks can be deleted in parallel

        c.      i.   RstudioShinyApp-Efs-RstudioStack-<instance>

                ii.  RstudioShinyApp-Efs-ShinyStack-<instance>

                ii.  RstudioShinyApp-Rstudio-Shiny-EcsCluster-<instance>

                The above three stacks can be deleted in parallel

        d.      i.   RstudioShinyApp-VPC-RstudioStack-<instance>

                ii.  RstudioShinyApp-Kms-RstudioStack-<instance>

                iii. RstudioShinyApp-Route53-Instance-Rstudio-Shiny-<instance>

                iv.  DataSyncTrigger-Rstudio-Trigger-Lambda-DataSync-and-SSMRole-<instance>

                The above four stacks can be deleted in parallel

2. From the central data account using AWS CloudFormation console:

        e.      i.   RstudioDataLake-S3-RstudioStack-<instance>

                ii.  RstudioDataLake-Dl-Resources-<instance>

                The above two stacks can be deleted in parallel

3. From the central network account using AWS CloudFormation console:

        f.      i.   RstudioNetwork-RstudioRoute53Stack-<instance>

                ii.  RstudioNetwork-Network-Account-Resources-<instance>

                The above two stacks can be deleted in parallel

4. Delete the ImportedDockerId secret from AWS Secrets Manager for the instance. You can use AWS CLI for this by running a command like below. --force-delete-without-recovery removes the secret instantaneously. You can also run a shell script to delete all the secrets for the instance.

                aws secretsmanager --profile <AWS CLI profile of central development account> delete-secret --secret-id <secret id>  --force-delete-without-recovery

6. To delete the pipeline, use

```
cdk destroy --profile <AWS CLI profile of central development account>
```

or delete the `Rstudio-Pipeline-Stack-<instance>` stack from AWS CloudFormation of central development account using AWS console of the AWS account.

## Notes on using Amazon ECS Exec

You can use Amazon ECS Exec (https://aws.amazon.com/blogs/containers/new-using-amazon-ecs-exec-access-your-containers-fargate-ec2/) to access the RStudio/Shiny containers. It is a preferred secure way to access containers on AWS ECS. The RStudio/Shiny containers are configured with Amazon ECS Exec.

Using the AWS CLI with SSM plugin installed, you can login to the containers with the commands below. `<instance>` is the value for instance parameter you passed in cdk.json.

```
export AWS_PROFILE=<profile name>
export AWS_REGION=<region name>
```
Get the task id of the container you want to login to from the task arn output using command below. The task id is the lst field of the task arn after the forward slash.

```
aws ecs --profile $AWS_PROFILE list-tasks --cluster Rstudio-Shiny-ecs-cluster-<instance>
```
With the task arn from command above, find the container name from the output of the command below. 

```
aws ecs --profile $AWS_PROFILE describe-tasks --tasks "<task_arn>" --cluster Rstudio-Shiny-ecs-cluster-<instance>
```
Start an ECS exec session:

```
aws ecs --profile $AWS_PROFILE execute-command  \
    --region $AWS_REGION \
    --cluster Rstudio-Shiny-ecs-cluster-<instance> \
    --task <task id> \
    --container <container name> \
    --command "/bin/bash" \
    --interactive
```

## Notes on using Athena

You can connect to Athena in the Central Data Account from your Rstudio container in the Rstudio deployment account.

Follow the steps below to connect to Athena from the RStudio IDE. The environment variables are loaded from R environment except ATHENA_USER and ATHENA_PASSWORD. Please modify the R environment file or use the values of these variables directly in the commands below from the RStudio IDE. Note that you should not store long term AWS credentials in the RStudio container.

        #verify Athena credentials by inspecting results from command below
        Sys.getenv()
        library(rJava)
        library(RJDBC)
        URL <- 'https://s3.amazonaws.com/athena-downloads/drivers/JDBC/SimbaAthenaJDBC-2.0.16.1000/AthenaJDBC42.jar'
        fil <- basename(URL)
        #download the file into current working directory
        if (!file.exists(fil)) download.file(URL, fil)
        #verify that the file has been downloaded successfully
        fil
        list.files()
        #set up driver connection to JDBC
        drv <- JDBC(driverClass="com.simba.athena.jdbc.Driver", "AthenaJDBC42.jar", identifier.quote="'")
        con <- jdbcConnection <- dbConnect(drv, Sys.getenv("JDBC_URL"), S3OutputLocation=Sys.getenv("S3_BUCKET"), Workgroup=Sys.getenv("ATHENA_WG"), User=Sys.getenv("ATHENA_USER"), Password=Sys.getenv("ATHENA_PASSWORD"))
        dbListTables(con)
        # run a sample query
        dfelb=dbGetQuery(con, "SELECT * FROM sampledb.elb_logs limit 10")
        head(dfelb,2)

Enjoy!



## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

