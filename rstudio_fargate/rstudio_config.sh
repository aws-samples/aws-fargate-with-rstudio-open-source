#!/bin/bash
######################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
######################################################################################

if [ -n "$4" ]; then
  echo "Updating secret resource profiles for account $1"
else
  echo "USAGE: ./rstudio_config.sh <profile of central development account> <kms key ARN for creating passwords in secrets manager> <profile of central data account> <comma separated profiles of rstudio deployment accounts>"
  exit 1
fi

cdk_json_change=false
arn_file_change=false
secret_arn=""
secret_arn_rstudio=""

IFS=","
read -r -a rstudio_profiles <<< "$4"
echo "${rstudio_profiles[*]}"
accounts=`cat cdk.json | jq -r '.context.rstudio_account_ids'`
users=`cat cdk.json | jq -r '.context.rstudio_users'`
instances=`cat cdk.json | jq -r '.context.instances'`
rstudio_individual_containers=`cat cdk.json | jq -r '.context.rstudio_individual_containers'`
data_account=`cat cdk.json | jq -r '.context.datalake_account_id'`
pipeline_account=`cat cdk.json | jq -r '.context.rstudio_pipeline_account_id'`
region=`cat cdk.json | jq -r '.context.datalake_aws_region'`
rstudio_image_repo=`cat cdk.json | jq -r '.context.rstudio_image_repo_name'`
shiny_image_repo=`cat cdk.json | jq -r '.context.shiny_image_repo_name'`
ssh_image_repo=`cat cdk.json | jq -r '.context.ssh_image_repo_name'`

principals=""

IFS=","
for account in $accounts
do
   set -f    
   principals="${principals},arn:aws:iam::${account}:root" 
done
IFS=""
principals="${principals:1}"

echo $principals

cp secret-resource-policy.json secret-resource-policy.json.`date '+%F_%H:%M:%S'`

eval "jq  '.Statement[0].Principal.AWS = (\"$principals\" | split(\",\"))'  secret-resource-policy.json > secret-resource-policy.json.tmp "

mv secret-resource-policy.json.tmp secret-resource-policy.json

IFS=","

cdk_json_backup="cdk.json."`date '+%F_%H:%M:%S'`
cp cdk.json "$cdk_json_backup"

arn_file_backup="rstudio_arn.txt."`date '+%F_%H:%M:%S'`

[[ -f rstudio_arn.txt ]] && cp rstudio_arn.txt "$arn_file_backup"

read -r -a individual_cont <<< "$rstudio_individual_containers"
counter=0

for instance in $instances
do
   for user in $users
   do
        user_name=`echo "$user"|tr "@" "_"|tr "." "_"`
		set -f
        pass=`aws secretsmanager --profile $1 get-random-password |jq -r .'RandomPassword'`            
   		secret_arn=`aws secretsmanager create-secret --profile $1 --name ImportedSecret-$user-Pass-$instance-$region --secret-string "$pass"  --kms-key-id "$2"|jq -r '.ARN'`
		if [ ! -z "$secret_arn" ]; then
        	aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedSecret-$user-Pass-$instance-$region --resource-policy file://secret-resource-policy.json
			#jq '.context += {"dummy_user_pass_arn": "dummy_password_arn"}' cdk.json >cdk.json.tmp
			echo "${user_name}_pass_arn_${instance}: ${secret_arn}" >>rstudio_arn.txt
			#sed -i 's/dummy_user_pass_arn/'"$user"'_pass_arn_'"$instance"'/g' cdk.json.tmp
        	#sed -i 's/dummy_password_arn/'"$secret_arn"'/g' cdk.json.tmp
        	#mv cdk.json.tmp cdk.json
			arn_file_change=true
			user_email+=("$user")
			echo $user_email
			secret_arn=""
		fi
    done

    if [ "${individual_cont[$counter]}" == "false" ]; then
		pass_rstudio=`aws secretsmanager --profile $1 get-random-password |jq -r .'RandomPassword'`
   		#secret_arn_rstudio=`aws secretsmanager create-secret --profile $1 --name ImportedSecretRstudio-$instance-Pass-$region --secret-string "$pass_rstudio"  --kms-key-id "$2"|jq -r '.ARN'|sed -e 's/^"//' -e 's/"$//'`
		secret_arn_rstudio=`aws secretsmanager create-secret --profile $1 --name ImportedSecretRstudio-$instance-Pass-$region --secret-string "$pass_rstudio"  --kms-key-id "$2"|jq -r '.ARN'`
		if [ ! -z "$secret_arn_rstudio" ]; then
   			aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedSecretRstudio-$instance-Pass-$region --resource-policy file://secret-resource-policy.json
   			#jq '.context += {"rstudio_instance_pass_arn": "dummy_password_arn"}' cdk.json >cdk.json.tmp
			echo "rstudio_${instance}_pass_arn: ${secret_arn_rstudio}" >>rstudio_arn.txt
   			#sed -i 's/rstudio_instance_pass_arn/rstudio_'"$instance"'_pass_arn/g' cdk.json.tmp
   			#sed -i 's/dummy_password_arn/'"$secret_arn_rstudio"'/g' cdk.json.tmp
   			#mv cdk.json.tmp cdk.json
			arn_file_change=true
			secret_arn_rstudio=""
		fi
    elif [ "${individual_cont[$counter]}" == "true" ]; then 
   		for user in $users
   		do
	    	user_name=`echo "$user"|tr "@" "_"|tr "." "_"`
			set -f
 	    	pass_rstudio=`aws secretsmanager --profile $1 get-random-password |jq -r .'RandomPassword'`
   	    	secret_arn_rstudio=`aws secretsmanager create-secret --profile $1 --name ImportedSecretRstudio-$instance-Pass-$user-container-$region --secret-string "$pass_rstudio"  --kms-key-id "$2"|jq -r '.ARN'`
			if [ ! -z "$secret_arn_rstudio" ]; then
   	    		aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedSecretRstudio-$instance-Pass-$user-container-$region --resource-policy file://secret-resource-policy.json
   	    		#jq '.context += {"rstudio_instance_user_container_pass_arn": "dummy_password_arn"}' cdk.json >cdk.json.tmp
				echo "rstudio_${instance}_${user_name}_container_pass_arn: ${secret_arn_rstudio}" >>rstudio_arn.txt
   	    		#sed -i 's/rstudio_instance_user_container_pass_arn/rstudio_'"$instance"'_'"$user"'_container_pass_arn/g' cdk.json.tmp
   	    		#sed -i 's/dummy_password_arn/'"$secret_arn_rstudio"'/g' cdk.json.tmp
	    		#mv cdk.json.tmp cdk.json
				arn_file_change=true
				secret_arn_rstudio=""
			fi
		done
    fi

    counter=`expr $counter + 1`
done   	

data_account_key_id=`awk '/'"$3"'/{flag=1; next} flag && /^aws_access_key_id/{print $NF; flag=0;}' ~/.aws/credentials`
secret_arn=`aws secretsmanager create-secret --profile $1 --name ImportedAccessKeyId-$data_account-$region --secret-string "$data_account_key_id"  --kms-key-id "$2"|jq -r '.ARN'`
if [ ! -z "$secret_arn" ]; then
	aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedAccessKeyId-$data_account-$region  --resource-policy file://secret-resource-policy.json
	jq 'del(.context.access_key_id_arn)' cdk.json
	jq '.context += {"access_key_id_arn": "dummy_keyid_arn"}' cdk.json >cdk.json.tmp	
	echo "access_key_id_arn: ${secret_arn}" >>rstudio_arn.txt
	sed -i 's/dummy_keyid_arn/'"$secret_arn"'/g' cdk.json.tmp
	mv cdk.json.tmp cdk.json
	cdk_json_change=true
	secret_arn=""
fi

data_account_key=`awk '/'"$3"'/{flag=1; next} flag && /^aws_secret_access_key/{print $NF; flag=0;}' ~/.aws/credentials`
secret_arn=`aws secretsmanager create-secret --profile $1 --name ImportedAccessKey-$data_account-$region --secret-string "$data_account_key"  --kms-key-id "$2"|jq -r '.ARN'`
if [ ! -z "$secret_arn" ]; then
	aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedAccessKey-$data_account-$region  --resource-policy file://secret-resource-policy.json
	jq 'del(.context.access_key_arn)' cdk.json
	jq '.context += {"access_key_arn": "dummy_key_arn"}' cdk.json >cdk.json.tmp
	echo "access_key_arn: ${secret_arn}" >>rstudio_arn.txt
	sed -i 's/dummy_key_arn/'"$secret_arn"'/g' cdk.json.tmp
	mv cdk.json.tmp cdk.json
	cdk_json_change=true
	secret_arn=""
fi

if [ ! -f ~/rstudio-dev-key.pub ]; then
	yes "y" | ssh-keygen -o -a 100 -t RSA -C "rstudio-dev-key rstudio-dev-key" -f ~/rstudio-dev-key -N ""
	pub_key=`cat ~/rstudio-dev-key.pub`
	secret_arn=`aws secretsmanager create-secret --profile $1 --name ImportedPubKey-$region --secret-string "$pub_key"  --kms-key-id "$2"|jq -r '.ARN'`
	if [ ! -z "$secret_arn" ]; then
		aws secretsmanager put-resource-policy --profile $1 --secret-id ImportedPubKey-$region --resource-policy file://secret-resource-policy.json
		jq 'del(.context.pubkey_arn)' cdk.json
		jq '.context += {"public_key_arn": "dummy_pubkey_arn"}' cdk.json >cdk.json.tmp
		echo "pubkey_arn: ${secret_arn}" >>rstudio_arn.txt
		sed -i 's/dummy_pubkey_arn/'"$secret_arn"'/g' cdk.json.tmp
		mv cdk.json.tmp cdk.json
		cdk_json_change=true
		secret_arn=""
	fi
fi

rstudio_dockerfile_change_var="FROM ${pipeline_account}.dkr.ecr.${region}.amazonaws.com/${rstudio_image_repo}:latest"
sed -i "/.dkr.ecr./ c $rstudio_dockerfile_change_var" `find . -name Dockerfile -print |grep rstudio`

shiny_dockerfile_change_var="FROM ${pipeline_account}.dkr.ecr.${region}.amazonaws.com/${shiny_image_repo}:latest"
sed -i "/.dkr.ecr./ c $shiny_dockerfile_change_var" `find . -name Dockerfile -print |grep shiny`

ssh_dockerfile_change_var="FROM ${pipeline_account}.dkr.ecr.${region}.amazonaws.com/${ssh_image_repo}:latest"
sed -i "/.dkr.ecr./ c $ssh_dockerfile_change_var" `find . -name Dockerfile -print |grep ssh`

if [ "$cdk_json_change" == false ]; then
	cp "$cdk_json_backup" cdk.json 
fi

if [ "$arn_file_change" == false ]; then
	cp "$arn_file_backup" rstudio_arn.txt 
fi

IFS=""
echo "${user_email[*]}"
for email in "${user_email[@]}"
do
	IFS=","
	for profile in "$rstudio_profiles"
	do
		aws ses --profile "$profile" verify-email-identity --email-address "$email"
   	done
	IFS=""
done



