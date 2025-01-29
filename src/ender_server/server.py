import socket 
import threading 
from eshu.src.Eshu.c2.msf.metasploit import Metasploit

import time
import os

def main():
    # Read Metasploit environment variables
    msf_host = os.getenv("MSF_HOST", "127.0.0.1")
    msf_port = int(os.getenv("MSF_PORT", 1337))
    msf_password = os.getenv("MSF_PASSWORD", "passwd")

    # Initialize and connect to Metasploit
    print("[+] Connecting to Metasploit...")
    try:
        msf = Metasploit(password=msf_password, server=msf_host, port=msf_port)
        print("[+] Successfully started and connected to Metasploit!")
    except Exception as e:
        print(f"[!] Failed to connect to Metasploit: {e}")

if __name__ == "__main__":
    # Ensure the script uses the environment variables from your setup
    os.environ["MSF_HOST"] = "10.1.1.2"
    os.environ["MSF_PORT"] = "1337"
    os.environ["MSF_PASSWORD"] = "memes"
    main()

