import os
import time
import socket
import threading
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

# ✅ Keep trying to connect to MSF RPC
def connect_msf():
    """Attempt to connect to Metasploit RPC server with retries."""
    print(f"[+] Connecting to Metasploit RPC at {MSF_HOST}:{MSF_PORT}...")

    start_msf_rpc()  # Start MSF RPC before connecting

    for _ in range(10):  # Retry 10 times
        try:
            msf = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
            print("[+] Successfully connected to Metasploit!")
            return msf
        except Exception as e:
            print(f"[!] Retrying MSF connection... {e}")
            time.sleep(2)  # Wait before retrying

    print("[!] Failed to connect to Metasploit after multiple attempts.")
    return None

# ✅ Create UDP Tracker Server
tracker_ip = "10.1.1.2"
tracker_port = 5000
tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tracker_socket.bind((tracker_ip, tracker_port))

def handle_message():
    """Handles UDP messages from clients."""
    while True:
        msg, peer_addr = tracker_socket.recvfrom(1024)
        decoded_msg = msg.decode()
        print(f"Received from {peer_addr}: {decoded_msg}")

        options = decoded_msg.split()
        command = options[0]

        if command == "connect":
            response = "[+] Connecting to MSF..."
            msf_client = connect_msf()
            if msf_client:
                response = "[+] Connected to Metasploit!"
        else:
            response = "Invalid command."

        tracker_socket.sendto(response.encode(), peer_addr)

def main():
    receive_thread = threading.Thread(target=handle_message)
    receive_thread.start()
    receive_thread.join()
    tracker_socket.close()

if __name__ == "__main__":
    main()
