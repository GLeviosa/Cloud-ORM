from client import Client

client = Client("us-east-2")

# client.forgeKey("Levis")
# client.assembleSecurityGroup("teste", "apenas um teste mesmo", [22,80])
client.launchInstance("teste")
client.launchInstance("teste0")
client.launchInstance("teste1")

client.terminateThemAll()

