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
"docker exec -it operator /bin/bash"
"python ender_client/client.py"
Enter: "connect"

To test search exploits / auxiliary, type "search exploit/auxiliary "module_name""
To test run exploit, type "run exploit/auxiliary "module_name""
Type in parameters when needed

Example of "run exploit" with scanner/ssh/ssh_login
Type "run auxiliary scanner/ssh/ssh_login"
For "USERNAME", type "msfadmin"
For "PASSWORD", type "msfadmin"
For "RHOSTS", type "10.1.1.3"
For "THREADS", type "5"
For "RPORT", press enter

Exploit should return
