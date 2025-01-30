import socket
import threading

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

name = input("Your name: ")
tracker_ip = "10.2.2.4"  # Server's IP
tracker_port = 5000  # Server's port

target_ip = "10.1.1.4"  # Target for attacks
target_port = 80

def handle_receive():
    """Receive messages from the server."""
    while True:
        try:
            message, server_addr = client_socket.recvfrom(1024)  # ✅ Fix
            decoded_msg = message.decode()
            print(f"Server ({server_addr}): {decoded_msg}")

            # Check if the message asks for exploit parameters
            if decoded_msg.startswith("Please enter parameters for"):
                exploit_name = decoded_msg.split(" ")[4]  # Extract the exploit name from the message
                print(f"Preparing to run exploit: {exploit_name}")

                # Prompt the user for RHOSTS, USERNAME, PASSWORD, and THREADS
                target_ip = input("Enter RHOSTS (target IP): ")
                username = input("Enter USERNAME: ")
                password = input("Enter PASSWORD: ")
                threads = input("Enter THREADS (number of threads): ")

                # Send the parameters back to the server
                params_message = f"{target_ip} {username} {password} {threads}"
                client_socket.sendto(params_message.encode(), server_addr)

                print(f"Sent parameters to server for exploit {exploit_name}")

            else:
                # Handle other messages from the server
                print(f"Received: {decoded_msg}")

        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def handle_send():
    """Send messages to the server."""
    start_index_exploits = 0  # Track pagination index for exploits
    start_index_auxiliary = 0  # Track pagination index for auxiliary modules

    while True:
        try:
            message = input(f"{name}: ")
            if message.lower() == 'exit':
                print("Exiting...")
                break
            
            elif message.lower() == 'connect':
                client_socket.sendto(message.encode(), (tracker_ip, tracker_port))
            
            elif message.lower().startswith('display exploits'):
                parts = message.split()
                if len(parts) == 3 and parts[2].isdigit():
                    start_index_exploits = int(parts[2])  # If user provides a number, use it
                else:
                    start_index_exploits = 0  # Default to first page

                client_socket.sendto(f"display exploits {start_index_exploits}".encode(), (tracker_ip, tracker_port))

            elif message.lower().startswith('display auxiliary'):
                parts = message.split()
                if len(parts) == 3 and parts[2].isdigit():
                    start_index_auxiliary = int(parts[2])  # If user provides a number, use it
                else:
                    start_index_auxiliary = 0  # Default to first page

                client_socket.sendto(f"display auxiliary {start_index_auxiliary}".encode(), (tracker_ip, tracker_port))

            elif message.lower() == 'next exploits':
                start_index_exploits += 20  # Increase pagination index for exploits
                client_socket.sendto(f"display exploits {start_index_exploits}".encode(), (tracker_ip, tracker_port))

            elif message.lower() == 'prev exploits' and start_index_exploits > 0:
                start_index_exploits -= 20  # Decrease pagination index for exploits
                client_socket.sendto(f"display exploits {start_index_exploits}".encode(), (tracker_ip, tracker_port))

            elif message.lower() == 'next auxiliary':
                start_index_auxiliary += 20  # Increase pagination index for auxiliary modules
                client_socket.sendto(f"display auxiliary {start_index_auxiliary}".encode(), (tracker_ip, tracker_port))

            elif message.lower() == 'prev auxiliary' and start_index_auxiliary > 0:
                start_index_auxiliary -= 20  # Decrease pagination index for auxiliary modules
                client_socket.sendto(f"display auxiliary {start_index_auxiliary}".encode(), (tracker_ip, tracker_port))

            elif message.lower().startswith('run exploit'):
                exploit_name = message.split(' ')[2]  # Extract exploit name
                client_socket.sendto(f"run exploit {exploit_name}".encode(), (tracker_ip, tracker_port))

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
