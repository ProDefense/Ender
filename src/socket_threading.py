import socket
import threading
import sys

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
            print(f" =============== SERVER Listening on {self.host}:{self.port} ===============")
            self.running = True
            self.handle_message()
            
            # while self.running:
            #     client_socket, client_address = self.server_socket.accept()
            #     print(f"[+] [Server] Server New connection from {client_address}")
            #     self.handle_client(client_socket, client_address)
            #     client_socket.close()
                
        except Exception as e:
            print(f"[-] Server Error starting server: {e}")
            sys.exit(1)
    
    # Multi threading
    # def accept_clients(self):
    #     while self.running:
    #         try:
    #             client_socket, client_address = self.server_socket.accept()
    #             print(f"[+] [Server] Server New connection from {client_address}")
    #             self.client.append(client_socket)
    #             client_thread = threading.Thread(target=self.handle_client, args = (client_socket, client_address))
    #             client_thread.start()
    #         except Exception as e:
    #             if self.running:
    #                 print(f"[-] [Server] Server Error accepting client: {e}")

    def handle_message(self):
        while self.running:
            try:
                data, client_address = self.server_socket.recvfrom(1024)
                decode_msg = data.decode('utf-8', errors ='ignore')
                print(f"[+] Server Received from {client_address}: {decode_msg}")

                if self.message_handler:
                    response = self.message_handler(decode_msg, client_address)
                    self.server_socket.sendto(response.encode('utf-8', errors ='ignore'), client_address)
                else:
                    self.server_socket.sendto(f"Echo: {decode_msg}".encode('utf-8'), client_address)
            except Exception as e:
                print(f"[-] Server Error with client {client_address}: {e}")

    def exit(self):
        self.running = False
        self.server_socket.close()
        print("[+] [Server] Server stopped")

class Client:
    def __init__(self, host='10.1.1.2', port= 4444):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.server_address = (self.host, self.port)

    def connect(self):
        # try:
        print(f"[Client] Connected to {self.host}:{self.port}")
        self.running = True
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()
        # except Exception as e:
        #     print(f"[Client] Error connecting to server: {e}")
        #     sys.exit(1)

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024)
                decoded_msg = data.decode('utf-8', errors='ignore')
                print(f"[Client] Received: {decoded_msg}")
            except Exception as e:
                if self.running:
                    print(f"[Client] Error receiving: {e}")
                break
        self.running = False
        self.client_socket.close()

    def send_message(self, message):
        try:
            self.client_socket.sendto(message.encode('utf-8', errors = 'ignore'), self.server_address)
        except Exception as e:
            print(f"[Client] Error sending message: {e}")

    def stop(self):
        self.running = False
        self.client_socket.close()
        print("[Client] Disconnected")