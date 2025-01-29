import socket 
import threading 
from eshu.src.Eshu.c2.msf.metasploit import Metasploit

import time
import os

players_data_base = {}
games_data_base = {}
scores = {}

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

        # if command == "register":
        #     response = register_player(options)
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
        # else:
        #     response =  "Please re-enter the command: "
        response = "I am Server, I am not BOOOTTTT!!!"

        tracker_socket.sendto(response.encode(), peer_addr)

def main():
    # # Read Metasploit environment variables
    # msf_host = os.getenv("MSF_HOST", "127.0.0.1")
    # msf_port = int(os.getenv("MSF_PORT", 1337))
    # msf_password = os.getenv("MSF_PASSWORD", "passwd")

    # # Initialize and connect to Metasploit
    # print("[+] Connecting to Metasploit...")
    # try:
    #     msf = Metasploit(password=msf_password, server=msf_host, port=msf_port)
    #     print("[+] Successfully started and connected to Metasploit!")
    # except Exception as e:
    #     print(f"[!] Failed to connect to Metasploit: {e}")

    receive_thread = threading.Thread(target = handle_message)
    receive_thread.start()
    receive_thread.join()
    tracker_socket.close()

if __name__ == "__main__":
    # Ensure the script uses the environment variables from your setup
    os.environ["MSF_HOST"] = "10.1.1.2"
    os.environ["MSF_PORT"] = "1337"
    os.environ["MSF_PASSWORD"] = "memes"
    main()

