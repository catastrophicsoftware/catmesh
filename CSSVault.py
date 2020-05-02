import hvac
import os
import time

vaultClient = hvac.Client(url=os.environ['CATMESH_VAULT_ADDR'],token=os.environ['CATMESH_VAULT_TOKEN'])


def requestAWSCredentialsV2(awsRoleName):
    print("Requesting AWS Credentials: " + awsRoleName)

    try:
        credResp = vaultClient.secrets.aws.generate_credentials(name=awsRoleName)
        
        #time.sleep(3) #wait 10 seconds for credentials to fully commit and become available

        return (
            credResp['data']['access_key'],
            credResp['data']['secret_key']
        )
    except Exception as ex:
        print("Exception Requesting AWS Credentials")
        print("Exception Details:" + str(ex))