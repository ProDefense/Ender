import socket
import threading
import sys

# ANSI color codes
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BLUE = "\033[34m"
RED = "\033[31m"
RESET = "\033[0m"

class Server:
    def __init__(self, host ='10.1.1.2', port = 1337, message_handler = None):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.message_handler = message_handler

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            print(f"{GREEN}=============== SERVER Listening on {self.host}:{self.port} ==============={RESET}")
            self.running = True
            self.handle_message()
                
        except Exception as e:
            print(f"{RED}[-] Server Error starting server: {e}{RESET}")
            sys.exit(1)
    

    def handle_message(self):
        while self.running:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                decode_msg = data.decode('utf-8', errors ='ignore')
                print(f"{GREEN}[+] Server Received from {client_address}: {decode_msg}{RESET}")

                if self.message_handler:
                    response = self.message_handler(decode_msg, client_address)
                    self.server_socket.sendto(response.encode('utf-8', errors ='ignore'), client_address)
                else:
                    self.server_socket.sendto(f"Echo: {decode_msg}".encode('utf-8'), client_address)
            except Exception as e:
                print(f"{RED}[-] Server Error with client {client_address}: {e}{RESET}")

    def exit(self):
        self.running = False
        self.server_socket.close()
        print(f"{BLUE}[+] [Server] Server stopped{RESET}")
        sys.exit(1)
        
class Client:
    def __init__(self, host='10.1.1.2', port= 4444):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.server_address = (self.host, self.port)
        self.response = None
        self.response_lock = threading.Lock()
        self.response_event = threading.Event()

    def connect(self):
        print(f"{BLUE}[SERVER] Connected to {self.host}:{self.port}{RESET}")
        self.running = True
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024)
                decoded_msg = data.decode('utf-8', errors='ignore')
                with self.response_lock:
                    self.response = decoded_msg
                    self.response_event.set()
                print(f"{BLUE}[SERVER] Received: {decoded_msg}{RESET}")
            except Exception as e:
                if self.running:
                    print(f"{RED}[Client] Error receiving: {e}{RESET}")
                break
        
        with self.response_lock:
            self.response = None
            self.response_event.clear()
        self.running = False
        self.client_socket.close()

    def send_message(self, message):
        try:
            self.client_socket.sendto(message.encode('utf-8', errors = 'ignore'), self.server_address)
        except Exception as e:
            print(f"{RED}[Client] Error sending message: {e}{RESET}")

    def wait_for_response(self):
        """Waiting for response from server"""
        self.response_event.wait()
        with self.response_lock:
            return self.response
    

    def stop(self):
        self.running = False
        with self.response_lock:
            self.response_event.set()

        self.client_socket.close()
        print(f"{GREEN}[Client] Disconnected{RESET}")

