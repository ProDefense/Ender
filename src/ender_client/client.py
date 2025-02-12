import socket
import threading
import json

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

name = input("Your name: ")
tracker_ip = "10.2.2.4"  # Server IP
tracker_port = 5000      # Server port

def handle_receive():
    """Receive messages from the server."""
    while True:
        try:
            message, server_addr = client_socket.recvfrom(65535)
            decoded_msg = message.decode().strip()

            # Attempt to parse as JSON
            try:
                msg_json = json.loads(decoded_msg)
            except:
                msg_json = None

            # If it's a PARAMS_REQUEST
            if msg_json and isinstance(msg_json, dict) and msg_json.get("action") == "PARAMS_REQUEST":
                module_type = msg_json.get("module_type")
                module_name = msg_json.get("module_name")
                options     = msg_json.get("options", [])

                print(f"\n[SERVER] The server wants parameters for {module_type}/{module_name}:\n")

                user_params_dict = {}
                for opt in options:
                    opt_name    = opt['name']
                    is_required = opt.get('required', False)
                    default_val = opt.get('default', '')
                    desc_val    = opt.get('desc', '')

                    prompt_str = f"[*] {opt_name}"
                    if desc_val:
                        prompt_str += f" ({desc_val})"
                    if default_val:
                        prompt_str += f" [default: {default_val}]"
                    prompt_str += ": "

                    user_input = input(prompt_str).strip()
                    # If user_input is empty but there's a default
                    if user_input == "" and default_val:
                        user_input = default_val

                    # If required and still empty, we could re-prompt. For now we just set empty.
                    if is_required and user_input == "":
                        print(f"[!] {opt_name} is required and has no default. Using empty string.")
                        # Possibly do a re-prompt loop if you want to force user input
                        # user_input = ...

                    user_params_dict[opt_name] = user_input

                # Send user params back to server
                params_json = json.dumps(user_params_dict)
                client_socket.sendto(params_json.encode(), server_addr)

            else:
                # Normal text from server
                if decoded_msg:
                    print(f"[SERVER] {decoded_msg}")
                else:
                    print("[!] Empty response from server? Possibly disconnected...")

        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def handle_send():
    """Send commands to the server."""
    while True:
        try:
            message = input(f"{name}: ").strip()
            if not message:
                # If user just hits Enter, skip
                continue

            if message.lower() == 'exit':
                print("Exiting...")
                client_socket.sendto(message.encode(), (tracker_ip, tracker_port))
                break
            else:
                # Send the typed message
                client_socket.sendto(message.encode(), (tracker_ip, tracker_port))

        except Exception as e:
            print(f"Error sending message: {e}")
            break

receive_thread = threading.Thread(target=handle_receive, daemon=True)
send_thread    = threading.Thread(target=handle_send)

receive_thread.start()
send_thread.start()
send_thread.join()
client_socket.close()
