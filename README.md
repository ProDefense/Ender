# Ender
Exploit Engine for Multiple C2s interlaced with Eshu for Post-Exploitation

First, docker compose up eshu
"cd eshu"
"docker compose up -d --build"

Next, go back to Ender directory
"cd .. "
"docker compose up -d --build"

test the connectivity between all 3 services
Terminal 1:
"docker exec -it ender-service /bin/bash"
"ping operator"
"ping metasploitable2"

Terminal 2:
"docker exec -it operator /bin/bash"
"ping ender-service"
"ping metasploitable2"

Terminal 3:
"docker exec -it metasploitable2 /bin/bash"
"ping ender-service"
"ping operator"

Testing the connectivity between server and metasploit
"docker exec -it ender-service /bin/bash"
"python ender_server/server.py"

To try out CLI
Terminal 1:
"docker exec -it operator /bin/bash"
"python ender_server/server.py"

Terminal 2:
"docker exec -it ender-client /bin/bash"
"python ender_client/client.py"
Enter: "connect"


