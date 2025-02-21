import socket
import threading
from socket_threading import Client

# client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# name = input("Your name: ")
# server_ip = "10.1.1.2"  # Server's IP
# server_port = 5000  # Server's port

# client_ip = "10.1.1.2"  # Target for attacks
# client_port = 80

# def handle_receive():
#     """Receive messages from the server."""
#     while True:
#         try:
#             message, server_addr = client_socket.recvfrom(1024)  # ✅ Fix
#             print(f"Server ({server_addr}): {message.decode()}")
#         except Exception as e:
#             print(f"Error receiving message: {e}")
#             break

# def handle_send():
#     """Send messages to the server."""
#     while True:
#         try:
#             message = input(f"{name}: ")
#             if message.lower() == 'exit':
#                 print("Exiting...")
#                 break
#             client_socket.sendto(message.encode(), (server_ip, server_port))
#         except Exception as e:
#             print(f"Error sending message: {e}")
#             break

# Start receiving and sending threads
# receive_thread = threading.Thread(target=handle_receive, daemon=True)
# send_thread = threading.Thread(target=handle_send)

# receive_thread.start()
# send_thread.start()

# send_thread.join()
# client_socket.close()

def main():
    # Create and connect the client
    client = Client(host='10.1.1.2', port= 4444)  # Customize host/port as needed
    client.connect()

    # Simple CLI to send messages
    try:
        while client.running:
            message = input("Enter message (or 'quit' to exit): ")
            if message.lower() == 'quit':
                client.stop()
                break
            client.send_message(message)
    except KeyboardInterrupt:
        client.stop()

if __name__ == "__main__":
    main()