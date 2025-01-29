import socket
import threading

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

name = input("Your name: ")
tracker_ip = "10.2.2.4"
tracker_port = "12345" #Example
target_ip = input("Please enter victim's ip: ")
target_port = int(input("Please enter victim port: "))

client_socket.bind((target_ip , target_port))

# print_lock = threading.Lock()

def handle_receive():
    """Receive messages from the server."""
    while True:
        try:
            message, _ = client_socket.recvfrom(1024)
            print(f"Server: {message.decode()}")
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
            print(f"Error seneding message: {e}")
            break


receive_thread = threading.Thread(target=handle_receive, daemon=True)
send_thread = threading.Thread(target=handle_send)

receive_thread.start()
send_thread.start()

# handle_send()
# receive_thread.join()
send_thread.join()
client_socket.close()