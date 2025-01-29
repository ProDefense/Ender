import socket 
import threading 
from eshu.src.Eshu.c2.msf.metasploit import Metasploit

import time
import os

players_data_base = {}
games_data_base = {}
scores = {}

def load_msf_config(file_path):
    """Load MSF configuration from a .env file."""
    config = {}
    try:
        with open(file_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):  # Ignore comments
                    key, value = line.strip().split("=", 1)
                    config[key] = value
    except FileNotFoundError:
        print(f"[!] msf_config.env not found at {file_path}")
        exit(1)
    return config

MSF_CONFIG_PATH = "eshu/src/config_files/msf_config.env"
msf_config = load_msf_config(MSF_CONFIG_PATH)

MSF_HOST = msf_config["MSF_HOST"]
MSF_PORT = msf_config["MSF_PORT"]
MSF_PASSWORD = msf_config["MSF_PASSWORD"]

#easy testing
# host = "10.10.1.1"
# port_tester = 12345

#Tracker Server Function
#create a UDP socket
tracker_ip = "10.2.2.4"
tracker_port = 5000

tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tracker_socket.bind((tracker_ip, tracker_port))
# tracker_socket.bind((host, port_tester))


def handle_message():
    
    while True:
        msg, peer_addr = tracker_socket.recvfrom(1024)
        decoded_msg = msg.decode()
        print(f"Received from {peer_addr}: {decoded_msg}")

        options = decoded_msg.split()
        command = options[0]

        if command == "connect":
            response = connect_msf()
        # elif command == "query":
        #     if options[1] == "players":
        #         response = query_players()
        #     elif options[1] == "games":
        #         response = query_games()
        # elif command == "start":
        #     response1, game_id = start_game(options)
        #     tracker_socket.sendto(response1.encode(), peer_addr)
        #     play_game(game_id)
        #     handle_message()

        # elif command == "end":
        #     response = end_games(options)
        # elif command == "de-register":
        #     response = deregister_player(options)
        else:
            response =  "Please re-enter the command: "

        tracker_socket.sendto(response.encode(), peer_addr)

def connect_msf():
    """Handles connection to the Metasploit RPC server."""
    print("[+] Connecting to Metasploit...")
    try:
        msf = Metasploit(password=MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT)
        print("[+] Successfully connected to Metasploit!")
        return "[+] Connected to Metasploit!"
    except Exception as e:
        print(f"[!] Failed to connect to MSF: {e}")
        return f"[!] Failed to connect: {e}"



def main():
    receive_thread = threading.Thread(target = handle_message)
    receive_thread.start()
    receive_thread.join()
    tracker_socket.close()

if __name__ == "__main__":
    main()

