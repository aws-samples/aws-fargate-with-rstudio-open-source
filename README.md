## Open Source RStudio/Shiny on AWS Fargate

This project delivers infrastructure code to run a scalable and highly available RStudio and Shiny Server installation on AWS utilizing various AWS services like Fargate, ECS, EFS, DataSync, S3 etc. The repository contains both the main project and subsets that host certain functionaliities from the main project in case you are only interested in deploying subsets of the entire project. The individual readmes within the folders contain deployment instructions for each project.

The development resources for the RStudio/Shiny deployment (AWS CodeCommit for hosting the AWS CDK in Python code, AWS CodePipeline for deployment of services, Amazon ECR repository for container images) are created in a central AWS account. From this account, AWS Fargate services for RStudio and Shiny along with the integrated services like Amazon ECS, Amazon EFS, AWS DataSync, AWS KMS, AWS WAF, Amazon ALB, and Amazon VPC constructs like Internet Gateway, NAT gateway, Security Groups, Route Tables are deployed into another AWS account. There can be multiple RStudio/Shiny accounts and instances to suit your requirements. You can also host multiple non-production instances of RStudio/Shiny in a single account.

The RStudio/Shiny deployment accounts obtain the networking information for the publicly resolvable domain from a central networking account and the data feed for the containers come from a central data repository account. Users upload data to the S3 buckets in the central data account or configure an automated service like AWS Service for SFTP to programmatically upload files. The uploaded files are transferred to the containers using AWS DataSync and Amazon EFS. The RStudio/Shiny containers are integrated with Amazon Athena for directly interacting with tables built on top of S3 data in the central data account.

It is assumed that AWS Shield or AWS Shield Advanced is already configured for the networking account, Amazon GuardDuty is enabled in all accounts along with AWS Config and AWS CloudTrail for monitoring and alerting on security events before deploying the infrastructure code. It is recommended that you use an egress filter for network traffic destined for the internet. The configuration of egress filter is not in scope for this codebase.

All services in this deployment are meant to be in one particular AWS region. The AWS services used in this architecture are managed services and configured for high availability. As soon as a service becomes unavailable, the service will automatically be brought up in the same Availability Zone (AZ) or in a different AZ within the same AWS Region.



Figure 1. RStudio/Shiny Open Source Deployment on AWS Serverless Infrastructure

Deployment

The infrastructure code provided in this repository creates all resources described in the architecture above.

Numbered items refer to Figure 1.

1. The infrastructure code is developed using AWS CDK for Python and used an AWS CodeCommit repository. 
2. The CDK stacks are integrated into AWS CodePipeline for automated builds. The stacks are segregated into four different stages and the stack are segregated by AWS services.
3. The container images used in the build are fetched from public Docker Hub using a pipeline are stored into Amazon ECR repositories for cross-account access. These images are accessed by the pipeline used to create the container in the deployment accounts.
4. Secrets like RStudio front-end password, public key for bastion containers and central data account access keys are configured in AWS Secrets Manager using an AWS KMS key and automatically passed into the deployment pipeline using parameters for cross-account access.
5. The central networking has the pre-configured base public domain. This is done outside the automated pipeline and the base domain info is passed on as a parameter in cdk.json
6. The base public domain will be delegated to the deployment accounts using AWS SSM Parameter Store.
7. An AWS Lambda function retrieves the delegated Route 53 zone for configuring the RStudio and Shiny sub-domains.
8. AWS Certificate Manager https certificates are applied on the RStudio and Shiny sub-domains
9. Amazon ECS cluster is created to control the RStudio, Shiny and Bastion containers and to scale up and down the number of containers as needed.
10. RStudio container is configured for the instance in a private subnet. RStudio container is not horizontally scalable for the Open Source version of RStudio. If you create only one container, the container will be configured for multiple front-end users. You can specify the user names in cdk.json. You can also create one RStudio container for each Data Scientist depending on your compute requirements. A cdk.json parameter will control your installation type. You can also control the container memory/vCPU using cdk.json. Further details are provided in the readme. If your compute requirements exceed Fargate container compute limits, you can use the EC2 launch type of Amazon ECS which offers a range of EC2 servers to fit your compute requirement. The code delivered with this blog caters for EC2 launch types as well controlled by the installation type paramter in cdk.json.
11. A bastion container will be created in the public subnet to help you ssh to RStudio and Shiny containers for administration tasks. The bastion container will be restricted by a security group and you can only access it from the IP range you provide in the cdk.json.
12. Shiny containers will be configured in the private subnet to be horizontally scalable. You can specify the number of containers and memory you need for Shiny Server in cdk.json.
13. Application Load Balancers are registered with RStudio and Shiny services for routing traffic to the containers and to perform health checks.
14. AWS WAF rules are built to provide additional security to RStudio and Shiny endpoints. You can specify whitelisted IPs in the WAF stack to restrict access to RStudio and Shiny from only allowed IPs.
15. Users will upload files to be analysed to a central data lake account either with manual S3 upload or programmatically using AWS Transfer for SFTP.
16. AWS DataSync will push files from Amazon S3 to cross-account Amazon EFS on an hourly interval schedule.
17. An AWS Lambda trigger will be configured to trigger DataSync transfer on demand outside of the hourly schedule for files that require urgent analysis. It is expected that bulk of the data transfer will happen on the hourly schedule and on demand trigger will only be used when necessary.
18. Amazon EFS file system will be attached to the containers for persistent storage. All containers will share the same file system. This is to facilitate deployment of Shiny Apps from RStudio containers using shared file system. This file system will live through container recycles.
19. You can create Amazon Athena tables on the central data account S3 buckets for direct interaction using JDBC from RStudio container. Access keys for cross account operation will be configured in the RStudio container R environment. It is recommended that you implement short term credential vending for this operation. 


Prerequisites

To deploy the CDK stacks, you should have the following prerequisites: 

1. Access to 4 AWS account (https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Fportal.aws.amazon.com%2Fbilling%2Fsignup%2Fresume&client_id=signup)s (minimum 3) for a basic multi-account deployment 
2. Permission to deploy all AWS services mentioned in the solution overview
3. Review RStudio and Shiny Open Source Licensing: AGPL v3 (https://www.gnu.org/licenses/agpl-3.0-standalone.html)
4. Basic knowledge of R, RStudio Server, Shiny Server, Linux, AWS Developer Tools (AWS CDK in Python, CodePipeline, CodeCommit), AWS CLI and AWS services mentioned in the solution overview
5. Review the readmes delivered with the code  and ensure you understand how the parameters in cdk.json control the deployment and how to prepare your environment to deploy the CDK stacks via the pipeline detailed below.

Installation

1. Create the AWS accounts to be used for deployment and ensure you have admin permissions access to each account. Typically, the following accounts are required:
        1. Central Development account - this is the account where the AWS Secret Manager parameters, CodeCommit repository, ECR repositories, and CodePipeline will be                  created.
        2. Central Network account - the Route53 base public domain will be hosted in this account
        3. Rstudio instance account - You can use as many of these accounts as required, this account will deploy RStudio and Shiny containers for an instance (dev, test,                uat, prod etc) along with a bastion container and associated services as described in the solution architecture.
        4. Central Data account - this is the account to be used for deploying the data lake resources - such as S3 bucket for picking up ingested source files  .
2. Install (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) AWS CLI and create (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-           files.html) AWS CLI profile for each account (pipeline, rstudio, network, datalake ) so that AWS CDK can be used
    Install (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html) AWS CDK in Python and bootstrap each account and allow the Central Development account to     perform cross-account deployment to all the other accounts.
3. export CDK_NEW_BOOTSTRAP=1
    npx cdk bootstrap --profile pipeline --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://<Central Development Account>/<Region>
  cdk bootstrap \
    --profile rstudio \
    --trust <Central Development Account> \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
    aws://<RStudio Deployment Account>/<Region>
   cdk bootstrap \
    --profile network \
    --trust <Central Development Account> \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
    aws://<Central Network Account>/<Region>
    cdk bootstrap \
    --profile datalake \
    --trust <Central Development Account> \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
    aws://<Central Data Account>/<Region>
4. Ensure you have a docker hub login account, otherwise you might get an error while pulling the container images from Docker Hub with the pipeline - You have reached your      pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits
5. Build the docker container images in Amazon ECR in the central development account by running the image build pipeline as instructed in the readme.
        1. Using the AWS console, create a CodeCommit repository to hold the source code for building the images - e.g. rstudio_docker_images
        2. Clone the GitHub repository and move into the rstudio_image_build folder
        3. Using the CLI - Create a secret to store your DockerHub login details as follows:
        4. aws secretsmanager create-secret --profile <profile of central development account> --name ImportedDockerId --secret-string '{"username":"<dockerhub username>",               "password":"<dockerhub password>"}'
        5. Create a CodeCommit repository to hold the source code for building the images - e.g. rstudio_docker_images and pass the repository name to the name parameter in              cdk.json for the image build pipeline
        6. Pass the account numbers (comma separated) where rstudio instances will be deployed in the cdk.json paramter rstudio_account_ids. Refer readme in                              rstudio_image_build folder.
        7. Synthesize the image build stack 
        8. cdk synth --profile <profile of central development account>
        9. Commit the changes into the CodeCommit repo you created using git
        10. Deploy the pipeline stack for container image build
        11. cdk deploy --profile <profile of central development account>
        12. Log into AWS console in the central development account and navigate to CodePipeline service. Monitor the pipeline (pipeline name is the name you provided in the             name parameter in cdk.json) and confirm the docker images build successfully.
6. Move into the rstudio-fargate folder
7. Provide the comma separated accounts where rstudio/shiny will be deployed in the cdk.json against the parameter rstudio_account_ids. 
8. Synthesize the stack Rstudio-Configuration-Stack in the Central Development account
   cdk synth Rstudio-Configuration-Stack --profile <profile of central development account> 
9. Deploy the Rstudio-Configuration-Stack. This stack should create a new CMK KMS Key to use for creating the secrets with AWS Secrets Maanger. The stack will output the AWS     ARN for the KMS key. Note down the ARN. Set the parameter "encryption_key_arn" inside cdk.json to the above ARN
    cdk deploy Rstudio-Configuration-Stack --profile <profile of rstudio deployment account>
10. Run the script rstudio_config.sh after setting the required cdk.json parameters. refer readme in rstudio_fargate folder.
    sh ./rstudio_config.sh <profile of the central development account> "arn:aws:kms:<region>:<profile of central development account>:key/<key hash>" <profile of central         data account> <comma separated profiles of the rstudio deployment accounts>
11. Run the script check_ses_email.sh with comma separated profiles for rstudio deployment accounts. This will check whether all user emails have been registed with Amazon       SES for all the rstudio deployment accounts in the region before you can deploy rstudio/shiny.
    sh ./check_ses_email.sh <comma separated profiles of the rstudio deployment accounts>
12. Before committing the code into the CodeCommit repository, synthesize the pipeline stack against all the accounts involved in this deployment. The reason behind this is        to ensure all the necessary context values are populated into cdk.context.json file and to avoid the DUMMY values being mapped. 
    cdk synth --profile <profile of the central development account>
    cdk synth --profile <profile of the central network account>
    cdk synth --profile <profile of the central data account>
    cdk synth --profile <repeat for each profile of the RStudio deplyment account>

13. Deploy the Rstudio Fargate pipeline stack
    cdk deploy --profile <profile of the central development account> Rstudio-Piplenine-Stack 
    Once the stack is deployed, monitor the pipeline by using the AWS CodePipeline service from the central development account. The name of the pipeline is RstudioDev.           Different stacks will be visible in AWS CloudFormation from the relevant accounts.

Notes about the Deployment

1. Once you have deployed RStudio and Shiny Server using the automated pipeline following the readme, you will be able to access the installation using a URL like below:

  Shiny server  -https://shiny.<instance>.build.<r53_base_domain> -- where instance and r53_base_domain are the values you specified in cdk.json

  If you mentioned individual_containers as false in cdk.json,
  RStudio Server - https://rstudio.<instance>.build.<r53_base_domain> -- where instance and r53_base_domain are the values you specified in cdk.json

  If you mentioned rstudio_individual_containers as true in cdk.json,
  RStudio Server - https://<user name>.rstudio.<instance>.build.<r53_base_domain> -- where user name, instance and r53_base_domain are the values you specified in cdk.json

2. For RStudio server, the default username is rstudio and the password is randomly generated and stored in AWS Secrets Manager. Individual user passwords are also randomly generated and stored in AWS Secrets Manager. Users will receive their passwords by email against the email ids configured in cdk.json. Only the users named rstudio will have sudo access in the containers.

3. To work with your dataset in RStudio, you will need to upload files in the S3 bucket in the Central Data account. There are two folders in the S3 bucket - one is for hourly scheduled file transfer and another is to trigger the data transfer as soon as the files arrive in the folder. These files are transferred to the EFS mounts (/s3_data_sync/hourly_sync and /s3_data_sync/instant_upload) which are mounted to all the RStudio and Shiny containers.

4. The RStudio and Shiny containers share another common EFS mount (/rstudio_shiny_share) for sharing shiny app files. RStudio containers (individual user containers) are configured with a different persistent EFS mount for /home in each container. The Shiny containers share a similar /home EFS mount.
  
5. The WAF rules will allow connection to Rstudio and Shiny containers only from the IPs/IP ranges you specify in cdk.json. If you do not want to restrict any IP, do not provide any value against the parameter allowed_ips in cdk.json.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

