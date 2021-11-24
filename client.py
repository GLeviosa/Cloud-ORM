import boto3
import os
from botocore.config import Config
from blender import bcolors


class Client():

    def __init__(self, region : str):

        self.region = region
        self.colors = bcolors()

        if region == "us-east-1":
            self.imageId = "ami-0279c3b3186e54acd"

        elif region == "us-east-2":
            self.imageId = "ami-020db2c14939a8efb"

        else:
            print(f"{self.colors.FAIL}Client does not support selected region;{self.colors.ENDC}")    
        
        self.config = Config(region_name=region)
        self.client = boto3.client("ec2", config=self.config)
        
    def forgeKey(self, name : str):
        print(f"{self.colors.HEADER}Heating the furnace up...{self.colors.ENDC}")

        filter = {
                "Name": "key-name",
                "Values": [name]
            }
        response = self.client.describe_key_pairs(Filters=[filter])

        if response["KeyPairs"]:
            answer = input(f"{self.colors.WARNING}KeyPair {name} already in use, do you wish to forge a new one? (Y/n):{self.colors.ENDC} ").lower()
            yes = ["", "y", "yes"]
            if answer in yes:
                response = self.client.delete_key_pair(KeyName=name)
                print(f"{self.colors.OKGREEN}KeyPair {name} successfully deleted!{self.colors.ENDC}")
            else:
                print(f"{self.colors.FAIL}Smithy has stopped working, try again later!{self.colors.ENDC}")
                return

        response = self.client.create_key_pair(KeyName=name)

        dir = "keychain/"+name+".pem"
        if os.path.exists(dir):
            os.remove(dir)

        file = open(dir, "w")
        file.write(response["KeyMaterial"])
        file.close()

        print(f"{self.colors.OKCYAN}The key has been forged and is ready to be wielded!{self.colors.ENDC}")

    def launchInstance(self, instanceName : str, todoScript="", securityGroup="default", instanceType="t2.micro", keyName="Levis"):
        print(f"{self.colors.HEADER}Getting ready for launch...{self.colors.ENDC}")

        floatingIp = self.client.allocate_address()["PublicIp"]
        instanceId = self.client.run_instances(
            ImageId = self.imageId,
            InstanceType = instanceType,
            UserData = todoScript,
            MaxCount = 1,
            MinCount = 1,
            KeyName = keyName,
            SecurityGroups = [securityGroup],
            TagSpecifications = [{
                "ResourceType" : "instance",
                "Tags" : [
                    {
                        "Key" : "Creator",
                        "Value" : "Giovanni"
                    },
                    {
                        "Key" : "Name",
                        "Value" : instanceName
                    }
                    
                ]
            }]
        )["Instances"][0]["InstanceId"]

        print(f"{self.colors.OKGREEN}Preparing to boot it up...{self.colors.ENDC}")

        garsson = self.client.get_waiter("instance_running")
        garsson.wait(InstanceIds=[instanceId])

        response = self.client.associate_address(
            InstanceId = instanceId,
            PublicIp = floatingIp
        )

        print(f"{self.colors.OKCYAN}Instance launched without failure:{self.colors.ENDC}")
        print(f" Name : {instanceName}")
        print(f" Id : {instanceId}")
        print(f" Public IPv4: {floatingIp}")
             

        return floatingIp

    def assembleSecurityGroup(self, name : str, description : str, ports : list):
        print(f"{self.colors.HEADER}Getting ready do assemble...{self.colors.ENDC}")
        filter = {
            "Name" : "group-name",
            "Values" : [name]
        }
        response = self.client.describe_security_groups(Filters=[filter])

        if response["SecurityGroups"]:
            answer = input(f"{self.colors.WARNING}SecurityGroup {name} already exists, do you wish to assemble a new one? (Y/n):{self.colors.ENDC} ").lower()
            yes = ["", "y", "yes"]
            if answer in yes:
                response = self.client.delete_security_group(GroupName=name)
                print(f"{self.colors.OKGREEN}SecurityGroup {name} successfully deleted!{self.colors.ENDC}")
            else:
                print(f"{self.colors.FAIL}Assembler has stopped working, try again later!{self.colors.ENDC}")
                return

        ipPermissions = []
        for port in ports:
            ipPermissions.append({
                "IpProtocol" : "tcp",
                "FromPort" : port,
                "ToPort" : port,
                "IpRanges" : [{"CidrIp" : "0.0.0.0/0"}]
            })

        vpcId = self.client.describe_security_groups()["SecurityGroups"][0]["VpcId"]

        securityGroupId = self.client.create_security_group(
            GroupName=name,
            Description=description
        )["GroupId"]

        response = self.client.authorize_security_group_ingress(GroupId=securityGroupId, IpPermissions=ipPermissions)

        print(f"{self.colors.OKCYAN}Security Group was assembled:{self.colors.ENDC}")
        print(f" ID : {securityGroupId}")
        print(f" Name : {name}")
        print(f" Description : {description}")
        print(f" Protocol : TCP ")
        print(f" Ip Range : {ports}")

    def terminateThemAll(self):
        print(f"{self.colors.HEADER}Come with me if you want to live...{self.colors.ENDC}")
        filterCreator = {
            "Name" : "tag:Creator",
            "Values" : ["Giovanni"]
        }
        filterRunning = {
            "Name" : "instance-state-name",
            "Values" : ["running"]
        }

        response = self.client.describe_instances(Filters=[filterCreator, filterRunning])

        reservations = response["Reservations"]
        instances = {}

        if reservations:
            for instance in reservations:
                for tag in instance["Instances"][0]["Tags"]:
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                instances[name] = {}
                instances[name]["id"] = instance["Instances"][0]["InstanceId"]
                instances[name]["ip"] = instance["Instances"][0]["PublicIpAddress"]

            for name, info in instances.items():
                print(f"{self.colors.OKBLUE}Hasta la vista {name}...{self.colors.ENDC}")
                allocationId = self.client.describe_addresses(PublicIps=[info["ip"]])['Addresses'][0]['AllocationId']   
                release_response = self.client.release_address(AllocationId=allocationId)

                terminate_response = self.client.terminate_instances(InstanceIds=[info["id"]])

                garsson = self.client.get_waiter("instance_terminated")
                garsson.wait(InstanceIds=[info["id"]])
                print(f"{self.colors.FAIL}Instance {name} is no longer with us.{self.colors.ENDC}")

        
        
        
