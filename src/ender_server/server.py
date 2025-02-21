import os
import time
import socket
import threading
from socket_threading import Server
from src.Eshu.c2.msf.metasploit import Metasploit

MSF_HOST = "10.1.1.2"  # Operator’s IP
MSF_PORT = 1337
MSF_PASSWORD = "memes"
RESOURCE_SCRIPT = "/usr/src/metasploit-framework/docker/msfconsole.rc"

def connect_msf():
    print("Initializing Eshu")
    
    # Ensure MSF RPC is running
    os.system("pkill msfrpcd")
    os.system(f"msfrpcd -P {MSF_PASSWORD} -S -p {MSF_PORT} -a {MSF_HOST} &")
    time.sleep(2)  # Wait for msfrpcd
    
    # Instantiate Eshu class
    msf_instance = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
    
    # Start msfconsole with resource script
    msf_instance.start_msfconsole_with_script(RESOURCE_SCRIPT)
    
    # Connect to MSF server (uses Eshu's retry logic)
    msf_instance.connect_to_msfserver()
    
    print("[+] Registered Metasploit with name 'msf'")
    return msf_instance.client

def handle_message(data, client_address):
    """Handle messages from clients."""
    print(f"[Server] Processing message: '{data}' from {client_address}")
    options = data.split()
    command = options[0] if options else ""

    if command == "connect":
        response = "[+] Connecting to MSF..."
        msf_client = connect_msf()
        response = "[+] Connected to Metasploit!" if msf_client else "[-] Failed to connect to Metasploit"
    else:
        response = "Invalid command."

    print(f"[Server] Sending response to {client_address}: {response}")
    return response

def main():
    # Create and start the server
    server = Server(host='10.1.1.2', port= 4444, message_handler=handle_message)  # Customize host/port as needed
    server.start()

    # Keep the server running until interrupted
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.exit()

if __name__ == "__main__":
    main()
