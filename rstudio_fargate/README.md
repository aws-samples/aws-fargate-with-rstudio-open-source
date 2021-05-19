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

# RStudio/Shiny project

This is a CDK application to deploy the infrastructure required for the RStudio/Shiny project using Serverless Architecture and
AWS Fargate.

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

RStudio Server Open Source Edition - https://www.rstudio.com/products/rstudio - AGPL-3.0
Shiny Server Open Source Edition - https://www.rstudio.com/products/shiny/shiny-server - AGPL-3.0

---

### Prerequisites:
* Access to at least four (minimum 3) AWS environments or accounts is required as follows:
- Central Development Account - this is the account where the AWS Secret Manager parameters, CodeCommit repository, ECR repositories, and CodePipeline will be created.
- Central Network Account - this is the central account where the Roure53 domain configurations are implemented.
- Rstudio instance Account -  You can use as many of these accounts as required, this account will deploy RStudio and Shiny containers for an instance (dev, test, uat, prod etc) along with a bastion container and associated services
- Central Data Account - this is the account where the analysis source files will be picked up for processing on the Rstudio/Shiny instances

If you use only 3 accounts, then install rstudio/shiny instances in the central development account.

### Installation Steps:

1. Setup your AWS CDK environment

    * A working python environment with pip and venv - for further details, follow the [CDK Getting started guide](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)

    The `cdk.json` file tells the CDK Toolkit how to execute your app. All the settings in this file should be configured before any deployment attempts are made.

    * Install (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) AWS CLI and create (https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) AWS CLI profile for each account (pipeline, rstudio, network, datalake ) so that AWS CDK can be used

    * Install (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html) AWS CDK in Python and bootstrap each account and allow the Central Development account to perform cross-account deployment to all the other accounts.

    This project is set up like a standard Python project.  The initialization process also creates a virtualenv within this project, stored under the `.venv` directory.  To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package. If for any reason the automatic creation of the virtualenv fails, 	you can create the virtualenv manually.

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
	$ pip install -r requirements.txt
	```  

	To add any additional dependencies, for example other CDK libraries, just add them to your `setup.py` file and rerun the `pip install -r requirements.txt` 	command.

2. Bootstrap accounts and configure trust for central development account in all the other accounts for cross-account deployment

    a.  export CDK_NEW_BOOTSTRAP=1
        npx cdk bootstrap --profile pipeline --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://<Central Development Account>/<Region>
    b.  cdk bootstrap \
        --profile rstudio \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<RStudio Deployment Account>/<Region>
    c. cdk bootstrap \
        --profile network \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<Central Network Account>/<Region>
    d. cdk bootstrap \
        --profile datalake \
        --trust <Central Development Account> \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://<Central Data Account>/<Region>

3. Create your base level public domain in the Network account and pass that value in the required cdk.json parameter

4. Before deploying this pipeline make sure the container image build pipeline (rstudio_build) is run first from the Central Development account. Refer to the readme for rstuio_build for installation instructions. rstudio_build pipeline will fetch the required public RStudio docker images from DockerHub and will store it into your Central Development account. Pass the created ECR repos in the required parameters in cdk.json for the rstudio deployment pipeline.

    a. Ensure you have a docker hub login account, otherwise you might get an error while pulling the container images from Docker Hub with the pipeline - You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits

    b. Clone the source code repository (https://github.com/aws-samples/aws-fargate-with-rstudio-open-source) using git clone. Move into the image-build folder.

    c. Using the CLI - Create a secret to store your DockerHub login details as follows:

        aws secretsmanager create-secret --profile <profile of central development account> --name ImportedDockerId --secret-string '{"username":"<dockerhub username>", "password":"<dockerhub password>"}'

    d. Using the AWS console, create a CodeCommit repository to hold the source code for building the images - e.g. rstudio_docker_images and pass this as the value for the name parameter in cdk.json for the image build pipeline. The pipeline will create three ECR repositories to hold the rstudio, shiny and openssh container images. The ECR repository names will be prefixed with the name parameter value from cdk.json. Assuming the prefix is rstudio_docker_images, the ECR repository names will be as follows:

        rstudio_docker_images_rstudio_image
        rstudio_docker_images_shiny_image
        rstudio_docker_images_openssh_image

    Pass these values as the parameter values in the rstudio instance deployment pipeline cdk.json for the parameters rstudio_image_repo_name, shiny_image_repo_name and ssh_image_repo_name respectively.

    e. Pass the account numbers (comma separated) where rstudio instances will be deployed in the cdk.json paramter rstudio_account_ids

    e. Synthesize the image build stack in the central development account

        cdk synth --profile <profile of central development account> 

    e. Commit the changes into CodeCommit repo you created in the central development account for the image build pipeline using git:
    To do this:<br/>You can obtain the clone https URL to the AWS code commit repository:
    ```
    https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    ```
    Link your local codebase with the upsteam CodeCommit repository using commands:<br/>
    ```
    $ git config --global credential.helper '!aws --profile <profile of the central development account> codecommit credential-helper $@'
    $ git remote add origin https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    $ git branch -u origin/master
    ```
    Commit your code into the Code Commit repository.
    ```
    $ git add .
    $ git commit -m 'My first commit'
    $ git push
    ```

    f. Deploy the pipeline stack for container image build in the central development account

        cdk deploy --profile <profile of central development account> 

    g. Log into AWS console in the central development account and navigate to CodePipeline service. Monitor the pipeline (pipeline name is the name you provided in the name parameter in cdk.json) and confirm the docker images build successfully. From this point onward you do not need to run cdk deploy to deploy this stack. The pipiline will automatically be triggered whenever you push changes to the CodeCommit reposirory by git push.

5. Move into the rstudio-fargate folder. Provide the comma separated accounts where rstudio/shiny will be deployed (rstudio deployment accounts) in the cdk.json against the parameter rstudio_account_ids. 

6. Synthesize the stack Rstudio-Configuration-Stack in the central development account
    cdk synth Rstudio-Configuration-Stack --profile <profile of Central Development account> 

7. Deploy the Rstudio-Configuration-Stack in the central development account. This stack should create a new CMK KMS Key to use for creating the secrets with AWS Secrets Maanger. The stack will output the AWS ARN for the KMS key. Note down the ARN. Set the parameter "encryption_key_arn" inside cdk.json to the above ARN

    cdk deploy Rstudio-Configuration-Stack --profile <profile of Central Development account>

8. Provide the instances, rstudio_account_ids, rstudio_users (email ids), rstudio_install_types, rstudio_individual_containers, KMS Key ARN, pipeline account id (central development account), central data account id, central data region and run the script rstudio_config.sh. The script take 3 parameter inputs - central development account profile, KMS Key ARN and central data account profile. This script will create all required secret manager parameters for the users, central data access keys and public keys to login to bastion container. The public and private key will be placed in the linux user home directory and will be named rstudio-dev-key for the private key and rstudio-dev-key.pub for the public key. This script created a file called rstudio_arn.txt which is used by the stacks. The script also updates the cdk.json and dockerfiles for the container images.

Make sure to provide email ids as usernames in the rstudio_users field. rstudio_config.sh will send verification emails using Amazon SES to the user ids. The users need to verify the emails before the rstudio pipeline is deployed. Each user will receive their password and the rstudio/shiny URLS via SES emails. Passwords for the default rstudio user will be sent to the sns_email_id value provided in cdk.json

    sh ./rstudio_config.sh <profile of the central development account> "arn:aws:kms:<region>:<profile of central development account>:key/<key hash>" <profile of central data account> <comma separated profiles of the rstudio deployment accounts>

Note that by default SES runs in test (sandbox) environment, this requires all the source and target email addresses verified as described above. To get your account out of test environment, you can open a ticket with AWS support from the SES page, for further details, you can refer to: https://docs.aws.amazon.com/ses/latest/DeveloperGuide/request-production-access.html

9. Configure cdk.json

    Configure the cdk.json to pass parameters for the vuild as per below:

    "instances": "demo,poc,uat" -- enter a list of comma separated rstudio/shiny instances. The rstudio/shiny URLs will be formed with this value as a subdomain

    "rstudio_account_ids": "xxxxxxxxxxxx,yyyyyyyyyyyy,zzzzzzzzzzzz" -- enter a list of comma separated AWS accounts where the rstudio instances will be deployed.  There should be as many accounts as the number of instances. You can deploy the instances in the same account if you want

    "rstudio_users": "testuser1,testuser2,testuser3" -- provide a list of comma separated fromt-end users for rstudio. All users will be created with the password you provide in the cdk.json for rstudio_pass_arn secret manager value

    "rstudio_install_types": "ec2,fargate,fargate" -- provide the ECS launch type(fargate/ec2) of your container for the rstudio container. This is to scale rstudio vertically as the open source rstudio does not allow running muliple containers on the same URL. Shiny will run multiple containers on Fargate and will scale horizontally. Bastion container will also run on Fargate.

    "rstudio_individual_containers": "false,true,false" -- This parameter is only relevant for faragte launch type in the parameter above. EC2 launch type will always run only one rstudio container. If this value is true, then one rstudio container for each user mentioned in rstudio_users parameter will be created on URLs like https://<user name>.rstudio.<instance>.build.<r53_base_domain> -- where user name, instance and base hosted zone are the values you specified in cdk.json. If this parameter is false, one rstudio container will be created with all the users mentioned in rstudio_users

    "rstudio_container_memory_in_gb":"8,4,8" -- provide the amount of memory for rstudio container for your instances, the number of vCPUs will be derived from the amount of memory; note that a fargate container can go up to 30GB/4vCPU max

    "shiny_container_memory_in_gb":"8,4,8" -- provide the amount of memory for shiny containers for your instances, the number of vCPUs will be derived from the amount of memory; note that a fargate container can go up to 30GB/4vCPU max

    "number_of_shiny_containers": 3 -- provide the number of shiny containers you want to configure for Shiny Server. These containers will be created with the same memory and vCPU as the Rstudio containers.

    "rstudio_ec2_instance_types": "t3.xlarge,xxxxx,yyyyyy" -- provide the EC2 instance type for the ECS cluster if the rstudio container will run on EC2 launch type of ECS

    "rstudio_pipeline_account_id": "nnnnnnnnnn" -- enter the account id of the central development account

    "rstudio_code_repo_name": "rstudio_fargate" -- enter the name for the AWS CodeCOmmit respository for the rstudio deployment pipeline

    "rstudio_image_repo_name": "rstudio_docker_images_rstudio_image" -- enter the Amazon ECR repository name for the rstudio docker container created by rstudio_build pipeline

    "shiny_image_repo_name": "rstudio_docker_images_shiny_image" -- enter the Amazon ECR repository name for the shiny docker container created by rstudio_build pipeline

    "ssh_image_repo_name": "rstudio_docker_images_openssh_image" -- enter the Amazon ECR repository name for the bastion ssh docker container created by rstudio_build pipeline

    "r53_base_domain": "xxx.xxx.xxx" -- enter the publicly resolvable route53 domain from which subdomains for rstudio and shiny will be derived. The base public domain can have multiple sobdomain levels

    "r53_sub_domain": "build" -- enter the subdomain which will be created from r53_base_domain and the new hosted zone will be delegated to create further subdomains and hosted zones in the rstudio deployment accouns. 

    "vpc_cidr_range": "10.5.0.0/16" -- provide the VPC CIDR range for your deployemnts

    "bastion_client_ip_range": "xxx.xxx.xxx.xxx/32" -- provide the client range from which you will access the bastion ssh container; you can modify the security group inbound rules as per your requirement after deployment

    "allowed_ips" : "205.251.237.80/28,205.251.237.96/28", -- provide the IP ranges that will be whitelisted in the AWS WAF for accessing Rstudio/Shiny. If no IPs are provided, rstudio/shiny will be accessible from all IPs.

    "sns_email_id": "xxxxxx@xxxx.com" -- provide the email to use for sns notifications for this pipeline

    "network_account_id": "wueyfulweflgh" -- provide the central network account where the base public route 53 domain resides. This domain will be delegated to the rstudio/shiny deployemnt accounts for configuring subdomains

    "datalake_account_id": "mnopqrstuvwx" -- provide the account id which will be used by users or sftp process to push files to S3. Files uploaded to S3 in this account will be synced to the EFS on the rstudio/shiny container in the rstudio/shiny deployment accounts

    "datalake_aws_region": "<region>" -- provide the region for the datalake account where files will be uploaded to S3

    "datalake_source_bucket_name": "rstudio-user-data-upload" -- provide the prefix for the S3 data upload bucket. The bucket name needs to be unique globally. The instance name provided as a parameter in cdk.json will be appended to this name

    "rstudio_athena_bucket_name": "xxxxxx-r-bucket-athena" -- provide the prefix for the s3 bucket to store output from athena queries run from the rstudio container. The bucket name needs to be unique globally. The instance name provided as a parameter in cdk.json will be appended to this name

    "rstudio_athena_wg_name": "xxxxxx-r-wg-athena" -- provide the prefix for the athena workgroup for running athena queries from the rstudio container. The instance name provided as a parameter in cdk.json will be appended to this name

    "datalake_source_bucket_key_hourly": "hourly_sync" -- provide the folder name in the datalake_source_bucket_name S3 bucket to be used for the hourly datasync from S3 to EFS mount for the containers

    "datalake_source_bucket_key_instant": "instant_sync" -- provide the folder name in the S3 bucket to be used for the datasync lambda trigger job from S3 to EFS mount for the containers

10. Run the script check_ses_email.sh with comma separated profiles for rstudio deployment accounts. This will check whether all user emails have been registed with Amazon SES for all the rstudio deployment accounts in the region before you can deploy rstudio. If email ids are not verified the rstudio pipeline will exit. It is controlled by the ses_email_verification_check parameter in cdk.json and the parameter is updated by check_ses_email.sh depending on validation results.

    sh ./check_ses_email.sh <comma separated profiles of the rstudio deployment accounts>

11. At this point you can now synthesize and deploy the stack for this application. Syntheisze the stacks against all the accounts involved in this deployment. The reason behind this is to ensure all the necessary context values are populated into cdk.context.json file and to avoid the DUMMY values being mapped. 

    	```cdk synth --profile <profile of the central development account>
    	cdk synth --profile <profile of the central network account>
    	cdk synth --profile <profile of the central data account>
    	cdk synth --profile <repeat for each profile of the RStudio deplyment account>```

12. Create a CodeCommit repo in the central development account and commit the source code using git. Obtain the clone https URL to the AWS code commit repository:
    ```
    https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    ```
    Link your local codebase with the upsteam CodeCommit repository using commands:<br/>
    ```
    $ git config --global credential.helper '!aws --profile <profile of the central development account> codecommit credential-helper $@'
    $ git remote add origin https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    $ git branch -u origin/master
    ```
    Commit your code into the Code Commit repository.
    ```
    $ git add .
    $ git commit -m 'My first commit'
    $ git push
    ```


13. This application is using the CdkPipeline construct - you simply deploy one stack (Rstudio-Piplenine-Stack) and the rest of the actions are
	peformed by the pipeline.

	### Deploying the stack:

	##### Synthesize and deploy the pipeline stack as follows:  
	`$ cdk synth --profile <profile of the central development account> Rstudio-Piplenine-Stack`   
	`$ cdk deploy --profile <profile of the central development account>  Rstudio-Piplenine-Stack`

	Once the pipeline stack is deployed successfully, log in to the AWS console in the central development account and navigate to the CodePipeline console to view the progress of the deployment.
    The name of the pipeline is RstudioDeploymentPipeline. 
    From this point onward you do not need to run cdk deploy to deploy this stack. The pipiline will automatically be triggered whenever you push changes to the CodeCommit reposirory by git push.

## Some useful CDK commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Notes on using the bastion container

From the bastion container, you can ssh to all the other containers in the instance. Make sure you have provided the right IP range in the cdk.json from where you will do the ssh. Otherwise, you can modify the security group for the bastion container to let your client machine through. Use the private key generated by rstudio_config.sh to ssh to bastion container public IP. The public IP is visible for the bastion conatiner task in the ECS console. The username to ssh to is ec2-user.It'll not require a password. ec2-user has passwordless sudo on the container. Save the private key genertaed by rstudio_config.sh on the bastion container. Use the private key to ssh to Shiny containers. The username is ec2-user. It'll not require a password. The ec2-user has passwordless sudo on the container. ssh to Rstudio containers will not require the private key but you will need the password for the rstudio fron end user to ssh to the rstudio container. You can either use the default rstudio user or the usernames you provide in cdk.json. The default rstudio user has sudo access on the container. The usernames you provide in cdk.json will not have sudo access in the container.

Enjoy!
