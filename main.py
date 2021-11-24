from client import Client

client_postgres = Client("us-east-2")
client_postgres.terminateThemAll()
client_django = Client("us-east-1")
client_django.terminateThemAll()

# print(open('postgres .sh','r').read())

client_postgres.forgeKey("Levis")
client_postgres.assembleSecurityGroup("postgresGroup", "SecurityGroup of PorstgreSQL", [22,80,8080,5432])
postgresIp = client_postgres.launchInstance("postgres",todoScript=(open('postgres.sh','r').read()),securityGroup="postgresGroup")

client_django.assembleSecurityGroup("djangoGroup", "SecurityGroup for Django", [22,8080])
djangoIp = client_django.launchInstance("django", todoScript=(open("django.sh", "r").read().replace("postgres_ip", postgresIp)), securityGroup="djangoGroup")
# client.launchInstance("teste0")
# client.launchInstance("teste1")

#

