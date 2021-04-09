# Data Transfer Demo
This is a CDK application to demonstrate a serverless data transfer from Amazon S3 to Amazon EFS on
AWS Fargate using AWS DataSync.

**WARNING!** Deploying this projet will create some AWS resources. make sure you are aware of the costs and be sure to destory the stack when you are done by running `cdk destory`

**NOTE**: Make sure that you have two working aws profiles (source and destination) which you can deploy to. Files will be uploaded
into a bucket located in the source account and they will be transferred to an Amazon EFS file system on the destination account.


---

### Prerequisites:
* A working python environment with pip and venv - for further details, follow the [CDK Getting started guide](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

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

To add any additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

At this point you can now synthesize and deploy the stacks for this code. 
**NOTE** The following sequence must be adhered to, else the deployment will fail.  
We do this in three parts - i.e. **Part 1** deploys the trigger Lambda function inside the destination account.  
**Part 2** deploys S3 bucket and event notification trigger into the source account, 
and **Part 3** deploys the DataSync Task and all related stacks(i.e. EFS and VPC stacks) into the destination account.

### Deploying the stacks:

##### Part 1: Deploy the trigger Lambda function to the destination account  
`$ cdk synth --profile destination LambdaStack`   
`$ cdk deploy --profile source LambdaStack`

##### Part 2: Deploy the S3 bucket and notification trigger into the source account

`$ cdk synth --profile source S3BucketStack`   
`$ cdk deploy --profile source S3BucketStack`

##### Part 3: Deploys the DataSync Task and all related stacks(i.e. EFS and VPC stacks) into the destination account,

`$ cdk synth --profile destination DataSyncStack`  
`$ cdk deploy --profile destination DataSyncStack`  

**NOTE** The above commands will also deploy `EfsStack, VpcStack, LambdaStack, KmsStack` automatically.


### Test the deployment:
After a successfull deployment, you can start testing the automatic file transfer.  
- Configure a Fargate [container](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_AWSCLI_Fargate.html)  
- Mount your EFS file system [onto the container](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html) for further details.  
- Upload a file into the source bucket located in the source account
- Connect to your ECS container instance using [SSH](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/instance-connect.html).  
- Confirm the file was tranferred successfully. Using the ssh session, navigate to the location of the mount point in the container and verify the file is there.

## Some useful CDK commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!