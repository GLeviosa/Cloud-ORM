from boto3 import client
from client import Client

clientFirst = Client()
clientFirst.terminateThemAll()
clientSecond = Client()
clientSecond.terminateThemAll()


clientFirst.forgeKey("postgres-g")

clientFirst.assembleSecurityGroup("postgresGroup", "SecurityGroup of PorstgreSQL", [22,80,8080,5432])
postgresIp = clientFirst.launchInstance("postgres",todo_script=(open('postgres.sh','r').read()),
                                            security_group="postgresGroup",key_name="postgres-g")

clientSecond.forgeKey("django-g")

clientSecond.assembleSecurityGroup("djangoGroup", "SecurityGroup for Django", [22,80,8080])
djangoIp = clientSecond.launchInstance("django", todo_script=(open("django.sh", "r").read().replace("postgres_ip", postgresIp)),
                                            security_group="djangoGroup", key_name="django-g")
                                            
djangoImageId = clientSecond.reflectImage("django_image", "django")
clientSecond.terminateInstance("django")
clientSecond.assembleSecurityGroup("loadBalancerGroup", "SecurityGroup for LoadBalancer", [22,80,8080])
clientSecond.createLoadBalancer("django-lb", "loadBalancerGroup")
clientSecond.createAutoScaling("django-as", "django-lb", djangoImageId)

# client = Client()
# client.terminateThemAll()
# client.launchInstance("teste")
# client.reflectImage("teste_image", "teste")
# client.terminateInstance("teste")
# client.assembleSecurityGroup("groupTest", "teste ",[80,8080])
# client.createLoadBalancer("teste-lb", "teste_image","groupTest")