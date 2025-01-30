# Ender
Exploit Engine for Multiple C2s interlaced with Eshu for Post-Exploitation

### First, docker compose up from Eshu Folder
"docker compose up -d --build"

### Next, build from Ender folder
"docker compose up -d --build"

### Setting Up Server and Client

Terminal 1:
"docker exec -it operator /bin/bash"
"msfconsole"
"load msgrpc Pass=memes ServerPort=1337 ServerHost=10.1.1.2"

To try out CLI
Terminal 2:
"docker exec -it ender-service /bin/bash"
"python ender_server/server.py"

Terminal 3:
"docker exec -it ender-service /bin/bash"
"python ender_client/client.py"
Enter: "connect"
***IMPORTANT*** Everytime the *client* seems to "hang", just hit enter to bring the next prompt.

Enter: "display exploits" or "display auxiliary" to start paging through options

Enter: "next exploits", "prev exploits", "next auxiliary", or "prev auxiliary" to navigate option pages (20 length)

Enter: "run exploit scanner/ssh/ssh_login"
***IMPORTANT*** To enter Parameters, you need to enter in order to bring up the prompts
Enter:
    '10.1.1.3/24' for RHOSTS
    'msfadmin' for USERNAME
    'msfadmin' for PASSWORD
    5 for THREADS


