import os
import time
import socket
import threading
from socket_threading import Server
from src.Eshu.c2.msf.metasploit import Metasploit

from socket_threading import RED, BLUE, GREEN, RESET

MSF_HOST = "10.1.1.2"
MSF_PORT = 1337
MSF_PASSWORD = "memes"
RESOURCE_SCRIPT = "/usr/src/metasploit-framework/docker/msfconsole.rc"

msfInstance = None

def connect_msf():
    msf_instance = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
    msf_instance.start_msfconsole_with_script(RESOURCE_SCRIPT)
    # msf_instance.connect_to_msfserver()  # Uncomment if needed
    print(f"{GREEN}[+] Registered Metasploit with name 'msf'{RESET}")
    return msf_instance.client

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
        numbered_exploits.append(f"{BLUE}[SERVER] Send 'next' for more or 'exit' to return to CLI{RESET}")
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

def run_msf_exploit(mname, target_ip, username, password, threads):
    """Run the selected exploit with parameters."""
    mtype = 'auxiliary'  # Change to 'exploit' if intended
    exploit = msfInstance.modules.use(mtype, mname)
    exploit["RHOSTS"] = target_ip
    exploit["USERNAME"] = username
    exploit["PASSWORD"] = password
    exploit["THREADS"] = threads
    print(f"{GREEN}Running exploit: {mname} on {target_ip} with {threads} threads...{RESET}")
    result = exploit.execute()
    print(f"{BLUE}Exploit Result: {result}{RESET}")
    if 'job_id' in result:
        return f"{BLUE}[+] Exploit scan started successfully.{RESET}"
    else:
        return f"{RED}[!] Scan failed.{RESET}"

def handle_message(data, client_address):
    """Handle messages from clients."""
    global msfInstance
    print(f"{BLUE}[Server] Processing message: '{data}' from {client_address}{RESET}")
    options = data.split()
    command = options[0].lower() if options else ""

    # Static variable to track search state per client
    if not hasattr(handle_message, 'search_state'):
        handle_message.search_state = {}
    client_state = handle_message.search_state.setdefault(client_address, {'keyword': None, 'start': 0, 'in_search': False})

    if command == "connect":
        response = f"{BLUE}[+] Connecting to MSF...{RESET}"
        msfInstance = connect_msf()
        response = f"{BLUE}[+] Connected to Metasploit!{RESET}" if msfInstance else f"{RED}[-] Failed to connect to Metasploit{RESET}"
        client_state['in_search'] = False  # Reset search state on connect
    
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