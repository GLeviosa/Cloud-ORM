import os, sys, stat, time
from types import resolve_bases
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from blender import bcolors
from tqdm import tqdm
import numpy as np

class Client():

    def __init__(self):
        self.colors = bcolors()
        self.instances = {}
        self.images = {}

        regionIsNotValid = True
        while regionIsNotValid:
            print(f"{self.colors.HEADER}Select a region to start working: {self.colors.ENDC}")
            answer = input(f"{self.colors.OKCYAN}[1] : North Virginia\n[2] : Ohio{self.colors.ENDC}\n>> ")

            if answer == "1":
                print(f"{self.colors.OKGREEN}\n>>> NORTH VIRGINIA <<<{self.colors.ENDC}")
                self.region = "us-east-1"
                self.imageId = "ami-0279c3b3186e54acd"
                regionIsNotValid = False
                
            elif answer == "2":
                print(f"{self.colors.OKGREEN}\n>>> OHIO <<<{self.colors.ENDC}")
                self.region = "us-east-2"
                self.imageId = "ami-020db2c14939a8efb"
                regionIsNotValid = False

            else:
                print(f"{self.colors.FAIL}Client does not support selected region, please select another one;{self.colors.ENDC}")

        self.config = Config(region_name=self.region)
        self.client = boto3.client("ec2", config=self.config)
        self.loadBalancer = boto3.client("elbv2", config=self.config)
        self.autoScaling = boto3.client("autoscaling", config=self.config)
        self.ec2_resource = boto3.resource("ec2")

        self.subnets = []
        for subnet in self.client.describe_subnets()["Subnets"]:
            self.subnets.append(subnet["SubnetId"])
        
    def forgeKey(self, name : str):
        print(f"{self.colors.HEADER}Heating the furnace up...{self.colors.ENDC}")

        filter = {
                "Name": "key-name",
                "Values": [name]
            }
        response = self.client.describe_key_pairs(Filters=[filter])

        if response["KeyPairs"]:
            answer = input(f"{self.colors.WARNING}KeyPair [{name}] already in use, do you wish to forge a new one? (Y/n):{self.colors.ENDC} ").lower()
            yes = ["", "y", "yes"]
            if answer in yes:
                response = self.client.delete_key_pair(KeyName=name)
                print(f"{self.colors.FAIL}Deleting Keypair [{name}]...{self.colors.ENDC}")
                waitBar(10)
                print(f"{self.colors.OKGREEN}KeyPair [{name}] successfully deleted!{self.colors.ENDC}")
            else:
                print(f"{self.colors.FAIL}Smithy has stopped working.{self.colors.ENDC}")
                return

        response = self.client.create_key_pair(KeyName=name)

        file_path = "keychain/"+name+".pem"
        if os.path.exists(file_path):
            os.remove(file_path)

        file = open(file_path, "x")
        file.write(response["KeyMaterial"])
        file.close()
        
        os.chmod(file_path, stat.S_IREAD)
        print(f"{self.colors.OKCYAN}The key has been forged and is ready to be wielded!{self.colors.ENDC}")

    def launchInstance(self, instance_name : str, todo_script="", security_group="default", instance_type="t2.micro", key_name="Levis", image=None):
        print(f"{self.colors.HEADER}Getting ready for launch...{self.colors.ENDC}")
        if image == None:
            image = self.imageId
        
        try:
            floatingIp = self.client.allocate_address()["PublicIp"]
        except ClientError as error:
            print(f"{self.colors.FAIL}Error allocating address, excluding excess...{self.colors.ENDC}")
        

        instanceId = self.client.run_instances(
            ImageId = image,
            InstanceType = instance_type,
            UserData = todo_script,
            MaxCount = 1,
            MinCount = 1,
            KeyName = key_name,
            SecurityGroups = [security_group],
            TagSpecifications = [{
                "ResourceType" : "instance",
                "Tags" : [
                    {
                        "Key" : "Creator",
                        "Value" : "Giovanni"
                    },
                    {
                        "Key" : "Name",
                        "Value" : instance_name
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
        print(f" Name : {instance_name}")
        print(f" Id : {instanceId}")
        print(f" Public IPv4: {floatingIp}")
             
        self.instances[instance_name] = {
            "id" : instanceId,
            "ip" : floatingIp
        }

        return floatingIp

    def assembleSecurityGroup(self, name : str, description : str, ports : list):
        print(f"{self.colors.HEADER}Getting ready do assemble...{self.colors.ENDC}")
        filter = {
            "Name" : "group-name",
            "Values" : [name]
        }

        try:
            response = self.client.describe_security_groups(Filters=[filter])

            if response["SecurityGroups"]:
                answer = input(f"{self.colors.WARNING}SecurityGroup {name} already exists, do you wish to assemble a new one? (Y/n):{self.colors.ENDC} ").lower()
                yes = ["", "y", "yes"]
                if answer in yes:
                    response = self.client.delete_security_group(GroupName=name)
                    print(f"{self.colors.FAIL}Deleting SecurityGroup [{name}]...{self.colors.ENDC}")
                    waitBar(10)
                    print(f"{self.colors.OKGREEN}SecurityGroup {name} successfully deleted!{self.colors.ENDC}")
                else:
                    print(f"{self.colors.FAIL}Assembler has stopped working.{self.colors.ENDC}")
                    return
        except ClientError as error:
            print(f"{self.colors.FAIL}Error while trying to delete SecurityGroup:\n{error}{self.colors.ENDC}")

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

    def terminateInstance(self, instance_name : str):
        print(f"{self.colors.HEADER}Getting ready to ter-mi-nate...{self.colors.ENDC}")
        if instance_name not in self.instances.keys():
            print(f"{self.colors.FAIL}Instance doesn't exist, perhaps another name.{self.colors.ENDC}")
            return

        allocationId = self.client.describe_addresses(PublicIps=[self.instances[instance_name]["ip"]])['Addresses'][0]['AllocationId']   
        release_response = self.client.release_address(AllocationId=allocationId)
        terminate_response = self.client.terminate_instances(InstanceIds=[self.instances[instance_name]["id"]])

        garsson = self.client.get_waiter("instance_terminated")
        garsson.wait(InstanceIds=[self.instances[instance_name]["id"]])
        print(f"{self.colors.FAIL}Instance {instance_name} is no longer with us.{self.colors.ENDC}")
    
        ip = self.instances[instance_name]["ip"]

    def terminateThemAll(self):
        print(f"{self.colors.HEADER}This is gonna be a massacre...{self.colors.ENDC}")
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
        try:
            print(f"{self.colors.WARNING}Deleting extra unused addresses...{self.colors.ENDC}")
            addresses = self.client.describe_addresses()["Addresses"]
            for address in addresses:
                if not address["InstanceId"]:
                    release = self.client.release_address(AllocationId=address["AllocationId"])
        except:
            print(f"{self.colors.OKBLUE}There were no extra addresses...{self.colors.ENDC}")
            pass
        
        response = self.loadBalancer.describe_load_balancers()

        loadBalancers = response["LoadBalancers"]
        if loadBalancers:
            for lb in loadBalancers:
                arn = lb["LoadBalancerArn"]
                tags = self.loadBalancer.describe_tags(ResourceArns=[arn])["TagDescriptions"][0]["Tags"]
                for tag in tags:
                    if "Creator" in tag.values() and "Giovanni" in tag.values():
                        print(f"{self.colors.OKBLUE}Hasta la vista {lb['LoadBalancerName']}...{self.colors.ENDC}")
                        self.loadBalancer.delete_load_balancer(LoadBalancerArn = arn)
                        garsson = self.loadBalancer.get_waiter("load_balancers_deleted")
                        garsson.wait(LoadBalancerArns=[arn])
                        print(f"{self.colors.FAIL}LoadBalancer {lb['LoadBalancerName']} is no longer with us.{self.colors.ENDC}")
                

        # response = self.autoScaling.describe_auto_scaling_groups

        

    def reflectImage(self, image_name : str, instance_name : str):
        if instance_name not in self.instances.keys():
            print(f"{self.colors.FAIL}Instance doesn't exist, perhaps another name will work.{self.colors.ENDC}")
            return
        filterCreator = {
            "Name" : "name",
            "Values" : [image_name]
        }

        response = self.client.describe_images(Filters=[filterCreator])

        if response["Images"]:
            imageId = response["Images"][0]["ImageId"]
            answer = input(f"{self.colors.WARNING}Image [{image_name}] already in use, do you wish to reflect a new one? (Y/n):{self.colors.ENDC} ").lower()

            if answer in ["", "y", "yes"]:
                response = self.client.deregister_image(ImageId=imageId)
                print(f"{self.colors.FAIL}Deleting Image [{image_name}]...{self.colors.ENDC}")
                waitBar(10)
                print(f"{self.colors.OKGREEN}Image [{image_name}] successfully deleted!{self.colors.ENDC}")
            else:
                print(f"{self.colors.FAIL}Mirror has stopped working.{self.colors.ENDC}")
                return

        filterCreator = {
            "Name" : "tag:Creator",
            "Values" : "Giovanni"
        }

        print(f"{self.colors.HEADER}Creating an image of instance [{instance_name}]{self.colors.ENDC}")
        instance_id = self.instances[instance_name]["id"]
        ami = self.client.create_image(InstanceId=instance_id, Name=image_name)
        self.images[image_name] = ami["ImageId"]
        garsson = self.client.get_waiter("image_available")
        garsson.wait(ImageIds=[ami["ImageId"]])

        print(f"{self.colors.OKCYAN}Your image has been reflected!{self.colors.ENDC}")
        print(f" ID : {ami['ImageId']}")
        print(f" Image Name : {image_name}")
        print(f" Reflected from : {instance_name}")

        return ami["ImageId"]

    def createLoadBalancer(self, lb_name : str, security_group_name : str):
        print(f"{self.colors.HEADER}Getting ready to create LoadBalancer...{self.colors.ENDC}")
        try:
            response = self.loadBalancer.describe_load_balancers(
                    Names=[lb_name]
                )
            if response["LoadBalancers"]:
                answer = input(f"{self.colors.WARNING}LoadBalancer [{lb_name}] already in use, do you wish to create a new one? (Y/n):{self.colors.ENDC} ").lower()
                if answer in ["", "y", "yes"]:
                    try:
                        response = self.loadBalancer.delete_load_balancer(LoadBalancerArn=response["LoadBalancers"][0]["LoadBalancerArn"])
                    except ClientError as error:
                        print(f"{self.colors.FAIL}Error while trying to delete LoadBalancer:\n{error}{self.colors.ENDC}")
                    print(f"{self.colors.FAIL}Deleting LoadBalancer [{lb_name}]...{self.colors.ENDC}")
                    garsson = self.loadBalancer.get_waiter("load_balancer_deleted")
                    garsson.wait(
                        LoadBalancerArn=response["LoadBalancers"][0]["LoadBalancerArn"],
                        Names=[lb_name]
                        )
                    print(f"{self.colors.OKGREEN}LoadBalancer [{lb_name}] successfully deleted!{self.colors.ENDC}")
                else:
                    print(f"{self.colors.FAIL}Libra has stopped working.{self.colors.ENDC}")
                    return
        except ClientError:
            pass
        
        

        filter = {
            "Name" : "group-name",
            "Values" : [security_group_name]
        }
        
        groupId = self.client.describe_security_groups(Filters=[filter])['SecurityGroups'][0]['GroupId']

        response = self.loadBalancer.create_load_balancer(
            Name = lb_name,
            Scheme = "internet-facing",
            Type = "application",
            Subnets = self.subnets,
            SecurityGroups = [groupId],
            Tags=[
                    {
                    "Key" : "Creator",
                    "Value" : "Giovanni"
                },
                {
                    "Key" : "Name",
                    "Value" : lb_name
                }
            ]

        )
        dns = response['LoadBalancers'][0]['DNSName']
        print(f"{self.colors.OKCYAN}LoadBalacer was created:{self.colors.ENDC}")
        print(f" DNS Name : {dns}")

        return dns

    def createAutoScaling(self, auto_scaling_name : str, load_balancer_name : str, image_id : str):
        try:
            response = self.autoScaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[auto_scaling_name]
            )

            if response["AutoScalingGroups"]:
                answer = input(f"{self.colors.WARNING}AutoScaling [{auto_scaling_name}] already in use, do you wish to create a new one? (Y/n):{self.colors.ENDC} ").lower()
                if answer in ["", "y", "yes"]:
                    response = self.autoScaling.delete_auto_scaling(AutoScalingGroupNames=auto_scaling_name,ForceDelete=True)
                    print(f"{self.colors.FAIL}Deleting AutoScaling [{auto_scaling_name}]...{self.colors.ENDC}")
                    waitBar(100)
                    print(f"{self.colors.OKGREEN}AutoScaling [{auto_scaling_name}] successfully deleted!{self.colors.ENDC}")
                else:
                    print(f"{self.colors.FAIL}AutoScaling has stopped working.{self.colors.ENDC}")
                    return

            response = self.autoScaling.describe_launch_configurations(
                LaunchConfigurationNames = [auto_scaling_name]
            )

            if response["LaunchConfigurations"]:
                answer = input(f"{self.colors.WARNING}LaunchConfigurations [{auto_scaling_name}] already in use, do you wish to create a new one? (Y/n):{self.colors.ENDC} ").lower()
                if answer in ["", "y", "yes"]:
                    response = self.autoScaling.delete_launch_configuration(
                        AutoScalingGroupNames=auto_scaling_name
                        )
                    print(f"{self.colors.FAIL}Deleting AutoScaling [{auto_scaling_name}]...{self.colors.ENDC}")
                    waitBar(10)
                    print(f"{self.colors.OKGREEN}LaunchConfigurations [{auto_scaling_name}] successfully deleted!{self.colors.ENDC}")
                else:
                    print(f"{self.colors.FAIL}LaunchConfigurations has stopped working.{self.colors.ENDC}")
                    return

        except ClientError:
            pass


        response_lconfig = self.autoScaling.create_lauch_configurations
        response = self.autoScaling.create_auto_scaling_group(
            AutoScalingGroupName = auto_scaling_name,
            LoadBalancerNames = [load_balancer_name],
            MinSize = 1,
            MaxSize = 3,
            DesiredCapacity = 1,
            InstanceId = image_id
        )
        
def waitBar(cicles : int):
    for i in tqdm(range(cicles)):
        time.sleep(np.random.uniform(0,1.5))