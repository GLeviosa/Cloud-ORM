import requests
from client import Client
import click
import json
import datetime
import sys

client = Client()
c = client.colors
response = client.loadBalancer.describe_load_balancers(
                
            Names=[
                'django-lb'
            ]
        )
if response['LoadBalancers']:
    
    dns = response['LoadBalancers'][0]['DNSName']

url = f'http://{dns}/tasks'

# instruction =  sys.argv[1]

running = True

while running:
    print(f"{c.HEADER}>>> WELCOME TO CLIENT <<<{c.ENDC}")
    print(f"{c.OKBLUE}You can do the following requests:{c.ENDC}")
    print(f"{c.OKCYAN}[1] : GET\n[2] : POST\n[3] : DELETE{c.ENDC}")
    answer = input(">> ")

    if answer == "1":
        response = requests.get(url + "/get")
        count = 1
        for task in response.json():
            print(f"{c.OKGREEN}TASK-{count}{c.ENDC}")
            print(f" Title : {task['title']}")
            print(f" Description : {task['description']}")
            print(f" Date Published : {task['pub_date']}\n")
            count += 1

    elif answer == "2":
        title = input(f"{c.OKBLUE}Title of task: {c.ENDC}")
        date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        description = input(f"{c.OKBLUE}Description of task: {c.ENDC}")
        payload = {
            "title":title,
            "pub_date":date,
            "description":description
        }
        response = requests.post(url + "/post", json=payload)
        rJSON = json.loads(response.text)
        print(f"{c.OKGREEN}TASK CREATED{c.ENDC}")
        print(f" Title : {rJSON['title']}")
        print(f" Description : {rJSON['description']}")
        print(f" Date Published : {rJSON['pub_date']}\n")

    elif answer == "3":
        confirm = input(f"{c.WARNING}Are you sure you want to delete all tasks? (Y/n): ")
        if confirm in ["y", "yes", ""]:
            response = requests.delete(url + "/delete")
            print(f"{c.FAIL}{response.text}{c.ENDC}\n")
    
    elif answer in ["q", "quit"]:
        running = False

    else:
        print(f"{c.WARNING}Command not found, type [quit] if you want to close the client.{c.ENDC}\n")