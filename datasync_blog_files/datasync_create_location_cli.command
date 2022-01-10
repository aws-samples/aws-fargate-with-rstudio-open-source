aws DataSync create-location-s3 --s3-bucket-arn 'arn:aws:s3:::YourBucketName' \  
	    --s3-config 'BucketAccessRoleArn=arn:aws:iam::account-id:role/DataSyncS3AccessRole' \  
	    --subdirectory /your-folder  

--Sample output:
	{  
	    "LocationArn": "arn:aws:DataSync:eu-west-1:<Account B's ID>:location/loc-00b5eccb098d4fb39"  
	}  
