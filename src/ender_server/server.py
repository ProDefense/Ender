import os
import socket
import threading
import time
import json  # For passing parameter data
from eshu.src.Eshu.c2.msf.metasploit import Metasploit

#####################
# Global Variables  #
#####################
msfInstance = None
MSF_CONFIG_PATH = "eshu/src/config_files/msf_config.env"

def load_msf_config(file_path):
    """Load MSF configuration from a .env file with default fallbacks."""
    config = {"MSF_HOST": "127.0.0.1", "MSF_PORT": 1337, "MSF_PASSWORD": "memes"}
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    config[key] = value
        # Ensure MSF_PORT is int
        config["MSF_PORT"] = int(config.get("MSF_PORT", 1337))
    except FileNotFoundError:
        print(f"[!] msf_config.env not found at {file_path}, using defaults.")
    except ValueError:
        print("[!] Invalid MSF_PORT in config, using default 1337.")
        config["MSF_PORT"] = 1337
    return config

msf_config = load_msf_config(MSF_CONFIG_PATH)
MSF_HOST = msf_config["MSF_HOST"]
MSF_PORT = msf_config["MSF_PORT"]
MSF_PASSWORD = msf_config["MSF_PASSWORD"]

#####################
# Metasploit Connect
#####################
def connect_msf():
    """Handles connection to the Metasploit RPC server."""
    print("[+] Connecting to Metasploit...")
    try:
        global msfInstance
        msfInstance = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
        print("[+] Successfully connected to Metasploit!")
        return "[+] Connected to Metasploit!"
    except Exception as e:
        print(f"[!] Failed to connect to MSF: {e}")
        return f"[!] Failed to connect: {e}"

#########################
# Display / Search funcs
#########################
def display_exploits(start=0, count=20):
    """Fetch and display exploits with pagination."""
    exploits = msfInstance.client.modules.exploits
    available_exploits = []
    end = start + count
    for exploit in exploits[start:end]:  
        available_exploits.append(f"Exploit Module: {exploit}")
    return available_exploits, len(exploits)

def display_auxiliary_modules(start=0, count=20):
    """Fetch and display auxiliary modules with pagination."""
    auxmods = msfInstance.client.modules.auxiliary
    available_aux = []
    end = start + count
    for aux in auxmods[start:end]:
        available_aux.append(f"Auxiliary Module: {aux}")
    return available_aux, len(auxmods)

def search_exploits(keyword, start=0, count=20):
    """Search for exploits containing the given keyword with pagination."""
    all_exploits = msfInstance.client.modules.exploits
    filtered = [exp for exp in all_exploits if keyword.lower() in exp.lower()]
    total = len(filtered)
    end = start + count
    return filtered[start:end], total

def search_auxiliary_modules(keyword, start=0, count=20):
    """Search for auxiliary modules containing the given keyword with pagination."""
    all_aux = msfInstance.client.modules.auxiliary
    filtered = [aux for aux in all_aux if keyword.lower() in aux.lower()]
    total = len(filtered)
    end = start + count
    return filtered[start:end], total

#####################
# Run MSF module
#####################
def run_msf_module(module_type, module_name, user_params):
    """
    Run a Metasploit module with user-supplied parameters.
    :param module_type: 'exploit' or 'auxiliary'
    :param module_name: The module name, e.g. 'scanner/ssh/ssh_login'
    :param user_params: Dictionary of parameter_name -> user_value
    """
    exploit = msfInstance.client.modules.use(module_type, module_name)
    if not exploit:
        return f"[!] Could not load {module_type} module: {module_name}"

    print(f"[+] Loaded {module_type}/{module_name}. Setting user parameters...")

    # Set user-supplied parameters
    for param_key, param_value in user_params.items():
        # If user left param_value blank but the module has a default, we could skip or use default
        if param_value.strip() == "" and param_key in exploit.options:
            continue
        exploit[param_key] = param_value

    # Execute the module
    result = exploit.execute()
    print("[+] Module execute() called. Result =>", result)
    return json.dumps(result)

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
        if module_name not in msfInstance.client.modules.exploits:
            return False, f"[!] {module_name} is NOT an exploit. Try: run auxiliary {module_name}"
    elif module_type == "auxiliary":
        # Check if it exists in the auxiliary list
        if module_name not in msfInstance.client.modules.auxiliary:
            return False, f"[!] {module_name} is NOT an auxiliary. Try: run exploit {module_name}"
    return True, None

#####################
# Socket Setup
#####################
tracker_ip = "10.2.2.4"
tracker_port = 5000
tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tracker_socket.bind((tracker_ip, tracker_port))

#####################
# Server Logic
#####################
def handle_message():
    while True:
        msg, peer_addr = tracker_socket.recvfrom(1024)
        decoded_msg = msg.decode().strip()
        print(f"Received from {peer_addr}: {decoded_msg}")

        # Split on whitespace
        options = decoded_msg.split()
        # If user typed nothing, skip
        if not options:
            # Could optionally send a "please type a command" response
            continue

        command = options[0].lower()

        if command == "connect":
            response = connect_msf()
            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "exit":
            print("Closing Ender...")
            break

        elif command == "display":
            # display exploits or display auxiliary
            if len(options) < 2:
                response = "Usage: display <exploits|auxiliary> [start_index]"
                tracker_socket.sendto(response.encode(), peer_addr)
                continue

            subtype = options[1].lower()
            start = int(options[2]) if len(options) > 2 else 0

            if subtype == "exploits":
                exploits, total = display_exploits(start)
                response = f"Showing {start} - {start+20} of {total} exploits:\n" + "\n".join(exploits)
            elif subtype == "auxiliary":
                auxiliaries, total = display_auxiliary_modules(start)
                response = f"Showing {start} - {start+20} of {total} auxiliary modules:\n" + "\n".join(auxiliaries)
            else:
                response = "Invalid display option. Use 'display exploits' or 'display auxiliary'."

            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "search":
            """
            Usage: search <exploits|auxiliary> <keyword> [start_index]
            e.g.  search exploits ms17 0
            """
            if len(options) < 3:
                response = ("Invalid search command.\n"
                            "Usage: search <exploits|auxiliary> <keyword> [start_index]")
                tracker_socket.sendto(response.encode(), peer_addr)
                continue

            module_type = options[1].lower()
            keyword = options[2]
            start = int(options[3]) if len(options) > 3 else 0

            if module_type == "exploits":
                results, total = search_exploits(keyword, start)
            elif module_type == "auxiliary":
                results, total = search_auxiliary_modules(keyword, start)
            else:
                response = "Invalid module type. Use 'search exploits' or 'search auxiliary'."
                tracker_socket.sendto(response.encode(), peer_addr)
                continue

            if results:
                response = (f"Search results for '{keyword}' "
                            f"({start}-{start+20} of {total}):\n" + "\n".join(results))
            else:
                response = f"No matches found for '{keyword}'."

            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "run":
            """
            Usage:
              run exploit <module_name>
              run auxiliary <module_name>
            """
            if len(options) < 3:
                response = (
                    "Invalid run command.\n"
                    "Correct usage: run exploit <module_name> OR run auxiliary <module_name>"
                )
                tracker_socket.sendto(response.encode(), peer_addr)
                continue

            module_type = options[1].lower()  # 'exploit' or 'auxiliary'
            module_name = options[2]

            # (Optional) Validate that the module_name is correct for the given module_type
            valid_ok, err_msg = validate_module_type(module_type, module_name)
            if not valid_ok:
                tracker_socket.sendto(err_msg.encode(), peer_addr)
                continue

            # Load the module to inspect its options
            exploit = msfInstance.client.modules.use(module_type, module_name)
            if not exploit:
                error_msg = f"[!] Could not load {module_type} module: {module_name}"
                tracker_socket.sendto(error_msg.encode(), peer_addr)
                continue

            # Build a structure describing each parameter
            module_options = []
            for opt_name, opt_data in exploit.options.items():
                # opt_data typically has keys like 'required', 'default', 'desc'
                required_flag = opt_data.get('required', False)
                default_val   = opt_data.get('default', "")
                desc_val      = opt_data.get('desc', "")
                module_options.append({
                    'name': opt_name,
                    'required': required_flag,
                    'default': default_val,
                    'desc': desc_val
                })

            # Convert to JSON so the client can parse
            param_request = {
                'action': 'PARAMS_REQUEST',
                'module_type': module_type,
                'module_name': module_name,
                'options': module_options
            }
            param_request_str = json.dumps(param_request)
            tracker_socket.sendto(param_request_str.encode(), peer_addr)

            # Now wait for the user-supplied params
            user_param_msg, _ = tracker_socket.recvfrom(65535)
            try:
                user_params = json.loads(user_param_msg.decode())
            except:
                response = "Could not parse user parameters JSON. Aborting."
                tracker_socket.sendto(response.encode(), peer_addr)
                continue

            # Run the module
            result = run_msf_module(module_type, module_name, user_params)
            tracker_socket.sendto(f"Exploit result: {result}".encode(), peer_addr)

        else:
            response = "Please re-enter the command."
            tracker_socket.sendto(response.encode(), peer_addr)

def main():
    receive_thread = threading.Thread(target=handle_message)
    receive_thread.start()
    receive_thread.join()
    tracker_socket.close()

if __name__ == "__main__":
    main()
