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

# Welcome to rstudio build!

This is a Python CDK pipeline to fetch the required public RStudio docker images from Docker Hub and to store it into your Central Development account. Pass the names of the created ECR repos in the required parameters in cdk.json for the rstudio deployment pipeline.

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
* Access to AWS environments or accounts is required as follows:
- Central Development Account - this is the account where the AWS Secret Manager parameters, CodeCommit repository, ECR repositories, and CodePipeline will be created.
- Rstudio instance Account -  You can use as many of these accounts as required, this account will deploy RStudio and Shiny containers for an instance (dev, test, uat, prod etc) along with a bastion container and associated services

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

2. Bootstrap central development account for CDK if it is not already bootstrapped:

    export CDK_NEW_BOOTSTRAP=1
    npx cdk bootstrap --profile pipeline --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://<Central Development Account>/<Region>

3. Ensure you have a docker hub login account, otherwise you might get an error while pulling the container images from Docker Hub with the pipeline - You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits

4. Clone the source code repository (https://github.com/aws-samples/aws-fargate-with-rstudio-open-source) using git clone. Move into the image-build folder.

5. Using the CLI - Create a secret to store your DockerHub login details as follows:

        aws secretsmanager create-secret --profile <profile of central development account> --name ImportedDockerId --secret-string '{"username":"<dockerhub username>", "password":"<dockerhub password>"}'

6. Using the AWS console, create a CodeCommit repository to hold the source code for building the images - e.g. rstudio_docker_images and pass this as the value for the name parameter in cdk.json for the image build pipeline. The pipeline will create three ECR repositories to hold the rstudio, shiny and openssh container images. The ECR repository names will be prefixed with the name parameter value from cdk.json. Assuming the prefix is rstudio_docker_images, the ECR repository names will be as follow:

        rstudio_docker_images_rstudio_image
        rstudio_docker_images_shiny_image
        rstudio_docker_images_openssh_image

    Pass these values as the parameter values in the rstudio instance deployment pipeline cdk.json for the parameters rstudio_image_repo_name, shiny_image_repo_name and ssh_image_repo_name respectively.

7. Pass the account numbers (comma separated) where rstudio instances will be deployed in the cdk.json paramter rstudio_account_ids

8. Synthesize the image build stack in the central development account

    cdk synth --profile <profile of central development account> 

9. Commit the changes into CodeCommit repo you created in the central development account for the image build pipeline using git:
    To do this:<br/>You can obtain the clone https URL to the AWS code commit repository:
    ```
    https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    ```
    Link your local codebase with the upsteam CodeCommit repository using commands:<br/>
    ```
    $ git config --global credential.helper '!aws --profile <profile of the central network account> codecommit credential-helper $@' <br/>
    $ git remote add origin https://git-codecommit.[aws-region].amazonaws.com/v1/repos/[codecommit-repository-name]
    $ git branch -u origin/master
    ```
    Commit your code into the Code Commit repository.
    ```
    $ git add .
    $ git commit -m 'My first commit'
    $ git push
    ```

10. Deploy the pipeline stack for container image build in the central development account

        cdk deploy --profile <profile of central development account> 

11. Log into AWS console in the central development account and navigate to CodePipeline service. Monitor the pipeline (pipeline name is the name you provided in the name parameter in cdk.json) and confirm the docker images build successfully. From this point onward you do not need to run cdk deploy to deploy this stack. The pipiline will automatically be triggered whenever you push changes to the CodeCommit reposirory by git push.


## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!


