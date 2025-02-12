import os
import socket
import threading
import time
from eshu.src.Eshu.c2.msf.metasploit import Metasploit

global msfInstance
# Load Metasploit config
MSF_CONFIG_PATH = "eshu/src/config_files/msf_config.env"

def load_msf_config(file_path):
    """Load MSF configuration from a .env file with default fallbacks."""
    config = {"MSF_HOST": "127.0.0.1", "MSF_PORT": 1337, "MSF_PASSWORD": "memes"}
    
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):  # Ignore comments
                    key, value = line.strip().split("=", 1)
                    config[key] = value

        # Ensure MSF_PORT is an integer
        config["MSF_PORT"] = int(config.get("MSF_PORT", 1337))  # Ensures valid integer
        
    except FileNotFoundError:
        print(f"[!] msf_config.env not found at {file_path}, using defaults.")

    except ValueError:
        print("[!] Invalid MSF_PORT in config, using default 1337.")
        config["MSF_PORT"] = 1337  # Fallback if port is invalid

    return config

msf_config = load_msf_config(MSF_CONFIG_PATH)
MSF_HOST = msf_config["MSF_HOST"]
MSF_PORT = msf_config["MSF_PORT"]
MSF_PASSWORD = msf_config["MSF_PASSWORD"]

# ✅ Automatically start MSF RPC inside the operator (Eshu)
def start_msf_rpc():
    """Send a command to start Metasploit RPC in the Eshu operator container."""
    operator_ip = "10.1.1.2"  # Update if necessary

    print(f"[+] Sending remote start command to {operator_ip}...")
    try:
        ssh_command = (
            f"ssh root@{operator_ip} 'msfconsole -q -x \"load msgrpc Pass={MSF_PASSWORD} "
            f"ServerPort={MSF_PORT} ServerHost=0.0.0.0; exit\"'"
        )
        os.system(ssh_command)
        print(f"[+] MSF RPC started on {operator_ip}:{MSF_PORT}")
    except Exception as e:
        print(f"[!] Failed to start MSF RPC remotely: {e}")

# ✅ Improved Metasploit Connection
def connect_msf():
    """Handles connection to the Metasploit RPC server."""
    print(f"[+] Checking MSF connection at {MSF_HOST}:{MSF_PORT}...")

    # Start Metasploit RPC if necessary
    start_msf_rpc()

    # Wait for MSF RPC to be ready
    for _ in range(10):  # Retry 10 times with 1s intervals
        try:
            global msfInstance
            msfInstance = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
            print("[+] Successfully connected to Metasploit!")
            return "[+] Connected to Metasploit!"
        except Exception as e:
            print(f"[!] MSF not ready yet, retrying... {e}")
            time.sleep(1)

    return "[!] Failed to connect after multiple attempts."

#Tracker Server Function
#create a UDP socket
tracker_ip = "10.2.2.4"
tracker_port = 5000

tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tracker_socket.bind((tracker_ip, tracker_port))

def handle_message():
    while True:
        msg, peer_addr = tracker_socket.recvfrom(1024)
        decoded_msg = msg.decode()
        print(f"Received from {peer_addr}: {decoded_msg}")

        options = decoded_msg.split()
        command = options[0]

        if command == "connect":
            response = connect_msf()
            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "display":
            if options[1] == "exploits":
                start = int(options[2]) if len(options) > 2 else 0
                exploits, total = display_exploits(start)
                response = f"Showing {start} - {start+20} of {total} exploits:\n" + "\n".join(exploits)
            elif options[1] == "auxiliary":
                start = int(options[2]) if len(options) > 2 else 0
                auxiliaries, total = display_auxiliary_modules(start)
                response = f"Showing {start} - {start+20} of {total} auxiliary modules:\n" + f"\n".join(auxiliaries)
            else:
                response = "Invalid display option. Use 'display exploits' or 'display auxiliary'."
            
            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "search":
            if options[1] == "exploits":
                keyword = options[2] if len(options) > 3 else ""
                exploits = search_exploits(keyword)
                response = f"Search results for '{keyword}':\n" + "\n".join(exploits) if exploits else "No exploits found."
            elif options[1] == "auxiliary":
                keyword = options[2] if len(options) > 3 else ""
                auxiliaries = search_auxiliary_modules(keyword)
                response = f"Search results for '{keyword}':\n" + "\n".join(auxiliaries) if auxiliaries else "No auxiliary modules found."
            else:
                response = "Invalid search command: search {exploits or auxiliary} {module keyword1/keyword2}"
            tracker_socket.sendto(response.encode(), peer_addr)

        elif command == "run" and options[1] == "exploit":
            exploit_name = options[2]
            tracker_socket.sendto(f"Please enter parameters for {exploit_name}:".encode(), peer_addr)
            
            params_msg, _ = tracker_socket.recvfrom(1024)
            params = params_msg.decode().split(' ')
            target_ip, username, password, threads = params[0], params[1], params[2], int(params[3])

            result = run_msf_exploit(exploit_name, target_ip, username, password, threads)
            tracker_socket.sendto(f"Exploit result: {result}".encode(), peer_addr)

        else:
            response = "Please re-enter the command."
            tracker_socket.sendto(response.encode(), peer_addr)

def search_exploits(keyword):
    """Search for exploits containing the given keyword."""
    exploits = msfInstance.client.modules.exploits
    return [exploit for exploit in exploits if keyword.lower() in exploit.lower()]

def search_auxiliary_modules(keyword):
    """Search for auxiliary modules containing the given keyword."""
    auxiliary_modules = msfInstance.client.modules.auxiliary
    return [aux for aux in auxiliary_modules if keyword.lower() in aux.lower()]

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
    
def display_exploits(start=0, count=20):
    """Fetch and display exploits with pagination."""
    exploits = msfInstance.client.modules.exploits
    available_exploits = []

    end = start + count
    for exploit in exploits[start:end]:  # Get exploits in chunks
        available_exploits.append(f"Exploit Module: {exploit}")

    return available_exploits, len(exploits)  # Return total exploits for pagination

def display_auxiliary_modules(start=0, count=20):
    """Fetch and display auxiliary modules with pagination."""
    auxiliary_modules = msfInstance.client.modules.auxiliary
    available_auxiliary = []

    end = start + count
    for aux in auxiliary_modules[start:end]:  # Get auxiliary modules in chunks
        available_auxiliary.append(f"Auxiliary Module: {aux}")

    return available_auxiliary, len(auxiliary_modules)  # Return total count for pagination

def run_msf_exploit(mname, target_ip, username, password, threads):
    """Run the selected exploit with parameters."""
    mtype = 'auxiliary'
    exploit = msfInstance.client.modules.use(mtype, mname)
    exploit["RHOSTS"] = target_ip
    exploit["USERNAME"] = username
    exploit["PASSWORD"] = password
    exploit["THREADS"] = threads

    print(f"Running exploit: {mname} on {target_ip} with {threads} threads...")
    result = exploit.execute()
    print("Exploit Result:", result)

    if 'job_id' in result:
        print("[+] Exploit scan started successfully.")
    else:
        print("[!] Scan failed.")
        
    return result



def main():
    receive_thread = threading.Thread(target = handle_message)
    receive_thread.start()
    receive_thread.join()
    tracker_socket.close()

if __name__ == "__main__":
    main()

