import hvac
import os
import cssutility
import time

vaultClient = hvac.Client(url=os.environ['CATMESH_VAULT_ADDR'],token=os.environ['CATMESH_VAULT_TOKEN'])


def requestAWSCredentialsV2(awsRoleName):
    cssutility.log("Requesting AWS Credentials: " + awsRoleName)

    try:
        credResp = vaultClient.secrets.aws.generate_credentials(name=awsRoleName)
        
        #time.sleep(3) #wait 10 seconds for credentials to fully commit and become available

        return (
            credResp['data']['access_key'],
            credResp['data']['secret_key']
        )
    except Exception as ex:
        cssutility.log("Exception Requesting AWS Credentials")
        cssutility.log("Exception Details:" + str(ex))