import socket
import threading

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

name = input("Your name: ")
tracker_ip = "10.2.2.4"  # Server's IP
tracker_port = 5000  # Server's port

target_ip = input("Please enter victim's IP: ")  # Target for attacks
target_port = int(input("Please enter victim port: "))

# ✅ REMOVE connect() → Not needed for UDP
# client_socket.connect((target_ip , target_port))  ❌ REMOVE THIS

def handle_receive():
    """Receive messages from the server."""
    while True:
        try:
            message, server_addr = client_socket.recvfrom(1024)  # ✅ Fix
            print(f"Server ({server_addr}): {message.decode()}")
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def handle_send():
    """Send messages to the server."""
    while True:
        try:
            message = input(f"{name}: ")
            if message.lower() == 'exit':
                print("Exiting...")
                break
            client_socket.sendto(message.encode(), (tracker_ip, tracker_port))
        except Exception as e:
            print(f"Error sending message: {e}")
            break

# Start receiving and sending threads
receive_thread = threading.Thread(target=handle_receive, daemon=True)
send_thread = threading.Thread(target=handle_send)

receive_thread.start()
send_thread.start()

send_thread.join()
client_socket.close()
