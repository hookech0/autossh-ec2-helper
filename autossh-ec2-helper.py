import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# --- CONFIG ---- #

AMI_ID = "ami-XYZ"
SEC_GROUP = "sg-XYZ"
SUBNET_ID = "subnet-XYZ"
INSTANCE_TYPE = "t2.micro"
REGION = "us-east-1"

# -------------- #

ec2 = boto3.client('ec2')

def auth_check():
      try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            return True
      except (NoCredentialsError, PartialCredentialsError):
            print ("[!] Failed to Authenticate to AWS...")
            return False
      except ClientError as e:
            print(f"[!] Authentication Error: {e.response['Error']['Message']}")
            return False

# Need to wait for the instance to be in a running state before we can allocate/associate an EIP
def wait_for_instance(instance_id):
     
     print(f"[i] Waiting for Instance {instance_id}")
     
     waiter = ec2.get_waiter('instance_running')
     waiter.wait(InstanceIds=[instance_id])
     print(f"\t[+] {instance_id} is now in a Running state\n")
    

def create_ec2(sshkey_name, owner_tag, name_tag, desc_tag):

    print(f"[i] Creating EC2 Instance with the Following: ")
    print(f"\tEC2 Name = {name_tag}")
    print(f"\tKeyName = {sshkey_name}")
    print(f"\tInstance Type = {INSTANCE_TYPE}")

    try:
        response = ec2.run_instances(
            ImageId=AMI_ID,
            InstanceType=INSTANCE_TYPE,
            KeyName=sshkey_name,
            MaxCount=1,
            MinCount=1,
            SubnetId=SUBNET_ID,
            SecurityGroupIds=[
                SEC_GROUP1,
                SEC_GROUP2
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags':[
                        {'Key': 'Name', 'Value': name_tag},
                        {'Key': 'Owner', 'Value': owner_tag},
                        {'Key': 'Description', 'Value': desc_tag}
                    ]
                }
            ]
        )

        instance_id = response['Instances'][0]['InstanceId']
        print("[+] New Instance Created:")
        print(f"\t{instance_id}")
        return instance_id
    
    except ClientError as e:
         print(f"[!] Failed to Create Instance: {e.response['Error']['Message']}")
         return None

def assign_eip(instance_id, name_tag):
    
      print(f"[i] Allocating EIP")

      try:
           
        response = ec2.allocate_address(
                Domain='vpc',
                TagSpecifications=[
                    {
                        'ResourceType': 'elastic-ip',
                        'Tags':[
                            {'Key': 'Name', 'Value': name_tag},
                        ]
                    }
                ]
        )

        allocation_id = response['AllocationId']
        public_ip = response['PublicIp']

        print("[+] EIP Allocated:")
        print(f"\t{allocation_id}")
        
        print("[i] Associating EIP")

        ec2.associate_address(
                AllocationId=allocation_id,
                InstanceId=instance_id
        )

        print("\t[+] EIP Associated\n")

        print("[===== New EC2 Details =====]")
        print(f"[Instance ID] {instance_id}")
        print(f"[EIP Alloc] {allocation_id}")
        print(f"[Public IP] {public_ip}")
        print("[===========================]")

      except ClientError as e:
           error_code = e.response['Error']['Code']
           error_msg = e.response['Error']['Message']

           if error_code == 'AddressLimitExceeded':
                print("[!] EIP limit reached. Release some unused EIPs or increase quota")
           elif error_code == 'InvalidInstanceID':
                print("[!] Cannot associate the EIP - Instance not ready or invalid")
           else:
                print("[!] EIP Assignment Error: {error_msg}")


def main():
      
    banner_width = 50

    print("=" * banner_width)
    print("Autossh EC2 Helper Script".center(banner_width))
    print("=" * banner_width + "\n")

    try:
         
        if auth_check():

            name_tag = input("Enter a name for the EC2 instance: ")
            sshkey_name = input("Enter your SSH key pair: ")
            owner_tag = input("Enter your name for the owner tag: ")
            desc_tag = input ("Enter a brief description for the EC2 instance: ")
            print("\n")

            instance_id = create_ec2(sshkey_name, owner_tag, name_tag, desc_tag)
            
            if instance_id:
                wait_for_instance(instance_id)
                assign_eip(instance_id, name_tag)
            else:
                print("[!] Failed to Create Instance")

        else:
            print("[!] Authentication Failed")
            print("\t Make sure you paste your AWS creds in the terminal")
            print("\t export AWS_ACCESS_KEY_ID=...")
        
    except Exception as e:
         print(f"[!] Unexpected Error: {e}")


if __name__ == "__main__":
    main()
