import os
import sys
import boto3
import urllib.request
import json
import time
from CSSVault import requestAWSCredentialsV2

print("CATMESH V 1.1.0")

hostedZoneID = os.environ['CATMESH_HOSTED_ZONE_ID']

clusterClients = {}
clusterServers = {}

ak,sk = requestAWSCredentialsV2('catmesh')
time.sleep(10) #required for aws to fully commit creds

ec2     = boto3.client('ec2', aws_access_key_id=ak, aws_secret_access_key=sk, region_name='us-west-2')
route53 = boto3.client('route53', aws_access_key_id=ak, aws_secret_access_key=sk, region_name='us-west-2')

cachedServiceNames = []

def lookupClusterMembers(tag, tagValue):
    try:
        print("QUERYING FOR INSTANCES WITH TAG: " + tag + " WITH VALUE: " + tagValue)

        instanceInfo = ec2.describe_instances(Filters=[
        {'Name' : 'tag:'+tag , 'Values' : [tagValue]}])

        numReservations = len(instanceInfo['Reservations'])
        print("NUM RESERVATIONS: " + str(numReservations))
        
        numInstances = 0
        instances = []
        reservations = instanceInfo['Reservations']

        for reser in reservations:
            numInstances += len(reser['Instances'])
            for instance in reser['Instances']:
                instances.append(instance)

        print("NUM INSTANCES: " + str(numInstances)) #total number of all intances in all reservations returned
        
        return instances
        #locatedServers = instanceInfo['Reservations'][0]['Instances']
        #print("LOCATED: " + str(len(locatedServers)) + "FROM INSTANCE QUERY")
    except Exception as ex:
        print("ERROR RETRIEVING CONSUL SERVERS")
        print("EXCEPTION DETAILS: " + str(ex))


def queryClusterServices(clusterServerAddr):
    try:
        queryURL = "http://" + clusterServerAddr + ":8500/v1/agent/services"

        with urllib.request.urlopen(queryURL) as resp:
            respData = resp.read()

        #return json.loads(respData.decode('utf-8'))
        locatedServices = json.loads(respData.decode('utf-8'))
        print("LOCATED: " + str(len(locatedServices)) + " ON CLUSTER CLIENT: " + clusterServerAddr)

        return locatedServices
    except Exception as ex:
        print("ERROR RETRIEVING CLUSTER SERVICES")
        print("EXCEPTION DETAILS: " + str(ex))


def createOrUpdateDNSRecord(recordName, recordAddress):
    print("CREATING DNS RECORD: " + recordName + ".cssoftware.online" + " WITH ADDRESS: " + recordAddress)
    apiResp = route53.change_resource_record_sets(
        HostedZoneId=hostedZoneID,
        ChangeBatch=
        {
            'Changes' : [
                {
                    'Action' : 'UPSERT',
                    'ResourceRecordSet' :
                    {
                        'Name' : recordName + ".cssoftware.online", #possibly doesn't need .cssoftware.online
                        'Type' : 'A',
                        'TTL' : 300,
                        'ResourceRecords' : [{'Value' : recordAddress}]
                    }
                }
            ]
        }
    )['ChangeInfo']
    print("ROUTE53 OPERATION ID: " + apiResp['Id'])
    print("ROUTE53 OPERATION STATUS: " + apiResp['Status'])



def updateClusterServiceDNSRecord(service):
    serviceName = service['Service']
    cachedServiceNames.append(serviceName)
    serviceAddress = service['Address']
    servicePort = service['Port']

    #loop through known cluster clients to locate same private ip as service
    for client in clusterClients:
        if client['State']['Name'] != "terminated":
            if client['PrivateIpAddress'] == serviceAddress: #this is the instance that the service is running on
                clientPublicIP = client['PublicIpAddress']
                createOrUpdateDNSRecord(serviceName, clientPublicIP)


#this is most likely not necessary since we will be processing the services on a client by client basis rather than grabbing all cluster services at once
'''
def processClusterServices(services):
    for service in services:
        splitID = service['ID'].split('-')
        if splitID[0] == "_nomad" and splitID[1] == "task": #We have located a cluster job / service
            updateClusterServiceDNSRecord(service)
'''


def main():
    global clusterClients
    global clusterServers

    #clusterServers = lookupClusterMembers('nomad-servers', 'auto-join') #lookup all cluster servers
    #clusterClients = lookupClusterMembers('nomad-clients', 'catcloud') #clients

    clusterServers = lookupClusterMembers(os.environ['CATCLOUD_SERVER_TAG_KEY'], os.environ['CATCLOUD_SERVER_TAG_VALUE'])
    clusterClients = lookupClusterMembers(os.environ['CATCLOUD_CLIENT_TAG_KEY'], os.environ['CATCLOUD_CLIENT_TAG_VALUE'])

    #clusterServers[0]['PrivateIpAddress'] is the VPC-local IP of the first cluster server

    #clusterServices = queryClusterServices(clusterServers[0]['PrivateIpAddress'])
    #processClusterServices(clusterServices)

    for server in clusterClients:
        if server['State']['Name'] != "terminated":
            #print("DEBUG SERVER DEFINITION: " + str(server))
            clientServices = queryClusterServices(server['PrivateIpAddress'])

            for service in clientServices:
                serviceDefinition = clientServices[service]
                splitID = serviceDefinition['ID'].split('-')
                if splitID[0] == "_nomad" and splitID[1] == "task": #We have located a cluster job / service
                    updateClusterServiceDNSRecord(serviceDefinition) #Create or update DNS record for this service
        else:
            print("SKIPPING TERMINATED INSTANCE!")


    #TODO: Only thing left to do after this point is look at existing records
    # And check to see which ones are no longer associated with an active service



#execute
main()