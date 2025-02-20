import socket
import threading
import sys

class Server:
    def __init__(self, host ='10.1.1.2', port = 1337, message_handler = None):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client = []
        self.running = False
        self.message_handler = message_handler

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f" =============== SERVER Listening on {self.host}:{self.port} ===============")
            self.running = True
            accept_thread = threading.Thread(target = self.accept_clients)
            accept_thread.start()
        except Exception as e:
            print(f"[-] Server Error starting server: {e}")
            sys.exit(1)
    
    def accept_clients(self):
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"[+] [Server] Server New connection from {client_address}")
                self.client.append(client_socket)
                client_thread = threading.Thread(target=self.handle_client, args = (client_socket, client_address))
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"[-] [Server] Server Error accepting client: {e}")

    def handle_client(self, client_socket, client_address):
        while self.running:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    print(f"[-] [Server] Server Client {client_address} disconnected")
                    break
                print(f"[+] [Server] Server Received from {client_address}: {data}")
                
                if self.message_handler:
                    response = self.message_handler(data, client_address)
                    client_socket.send(response.encode('utf-8'))
                else:
                    # Default echo behavior if no handler is provided
                    client_socket.send(f"Echo: {data}".encode('utf-8'))
                    
            except Exception as e:
                print(f"[-] [Server] Server Error with Client {client_address} : {e}")
                break
        
        self.client.remove(client_socket)
        client_socket.close()

    def exit(self):
        self.running = False

        for client in self.client:
            client.close()

        self.server_socket.close()
        print("[+] [Server] Server stopped")

class Client:
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"[Client] Connected to {self.host}:{self.port}")
            self.running = True
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.start()
        except Exception as e:
            print(f"[Client] Error connecting to server: {e}")
            sys.exit(1)

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    print("[Client] Server disconnected")
                    break
                print(f"[Client] Received: {data}")
            except Exception as e:
                if self.running:
                    print(f"[Client] Error receiving: {e}")
                break
        self.running = False
        self.client_socket.close()

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"[Client] Error sending message: {e}")

    def stop(self):
        self.running = False
        self.client_socket.close()
        print("[Client] Disconnected")