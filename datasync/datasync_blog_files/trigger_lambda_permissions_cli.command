aws lambda add-permission --profile AccountB \  
    --region <region> \  
    --function-name test-DataSync-instant-upload \  
    --statement-id "GiveS3PermissionToExecute" \  
    --principal s3.amazonaws.com \  
    --action lambda:InvokeFunction \  
    --source-arn arn:aws:s3:::<bucket-name> \  
    --source-account <account-a-id>
