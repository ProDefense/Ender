# Ender
Exploit Engine for Multiple C2s interlaced with Eshu for Post-Exploitation

Go to Ender directory
"docker compose up -d --build"

Testing the connectivity between server and metasploit

To try out CLI
Terminal 1:
"docker exec -it operator /bin/bash"
"python ender_server/server.py"

Terminal 2:
"docker exec -it ender-client /bin/bash"
"python ender_client/client.py"
Enter: "connect"


