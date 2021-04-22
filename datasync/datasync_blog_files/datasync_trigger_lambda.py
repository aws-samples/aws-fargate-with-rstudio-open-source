import json  
import boto3  
import os  
  
DataSync_task_arn = 'arn:aws:datasync:<Region>:<Account B’s ID>:task/<Task ID>'  
  
# Let's use Amazon DataSync  
DataSync = boto3.client('DataSync')  
      
def lambda_handler(event, context):  
    objectKey = ''  
    try:  
        objectKey = event["Records"][0]["s3"]["object"]["key"]  
    except KeyError:  
        raise KeyError("Received invalid event - unable to locate Object key to upload.", event)  
          
    response = DataSync.start_task_execution(  
        TaskArn=DataSync_task_arn,  
        OverrideOptions={  
        },  
        Includes=[  
            {  
                'FilterType': 'SIMPLE_PATTERN',  
                'Value': '/' + os.path.basename(objectKey)  
            }  
        ]  
    )  
      
    return {  
        'response' : response  
    } 
