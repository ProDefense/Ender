import os
import time
import socket
import threading
from socket_threading import Server
from src.Eshu.c2.msf.metasploit import Metasploit

# Metasploit Configurations
MSF_HOST = "10.1.1.2"  # Operator container IP
MSF_PORT = 1337
MSF_PASSWORD = "memes"

# ✅ Auto-start Metasploit in the Operator container
def start_msf_rpc():
    """Start Metasploit RPC inside the operator container."""
    print(f"[+] Starting Metasploit RPC in {MSF_HOST}...")
    try:
        ssh_command = (
            f"ssh root@{MSF_HOST} 'msfconsole -q -x \"load msgrpc Pass={MSF_PASSWORD} "
            f"ServerPort={MSF_PORT} ServerHost=0.0.0.0; exit\"'"
        )
        os.system(ssh_command)
        print(f"[+] MSF RPC started on {MSF_HOST}:{MSF_PORT}")
    except Exception as e:
        print(f"[!] Failed to start MSF RPC: {e}")

def connect_msf():
    """Attempt to connect to Metasploit RPC server with retries until success."""
    print(f"[+] Connecting to Metasploit RPC at {MSF_HOST}:{MSF_PORT}...")

    start_msf_rpc()  # Start MSF RPC before connecting

    while True:  # Retry indefinitely
        try:
            msf = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
            print("[+] Successfully connected to Metasploit!")
            return msf
        except Exception as e:
            print(f"[!] Retrying MSF connection... {e}")
            time.sleep(2)  # Wait 2 seconds before retrying (adjust as needed)
            
# ✅ Create UDP Tracker Server
# server_ip = "10.1.1.2"
# server_port = 5000
# server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# server_socket.bind((server_ip, server_port))

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
    server = Server(host='10.1.1.2', port=1337, message_handler=handle_message)  # Customize host/port as needed
    server.start()

    # Keep the server running until interrupted
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.exit()

if __name__ == "__main__":
    main()
