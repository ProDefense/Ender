import socket
import subprocess
import threading
from socket_threading import Client
from socket_threading import GREEN, CYAN, RED, RESET

class SyncClient(Client):
    """Extended Client class for synchronous communication."""
    def send_and_wait(self, message):
        """Send a message and wait for the server’s response."""
        with self.response_lock:
            self.response = None  # Clear previous response
            self.response_event.clear()  # Reset event
        self.send_message(message)  # Send the command via UDP
        # print(f"{CYAN}[Client] Sent: '{message}'{RESET}")
        response = self.wait_for_response()  # Wait indefinitely, protected by mutex
        return response

def main():
    # Create and connect the client
    client = SyncClient(host='10.1.1.2', port=4444)
    client.connect()

    # Simple CLI to send messages and wait for responses
    try:
        while client.running:
            message = input(f"{GREEN}Enter message (or 'quit' to exit): {RESET}").strip()

            if not message:
                print(f"{RED}[Client] Empty command. Please enter a valid command.{RESET}")
                continue

            if message.lower() == 'quit':
                    client.send_message(message)
                    client.stop()
                    break

            # Ensure Meterpreter commands are formatted correctly
            elif message.startswith("meterpreter"):
                parts = message.split(maxsplit=2)
                if len(parts) < 3:
                    print(f"{RED}[Client] Usage: meterpreter <session_id> <command>{RESET}")
                else:
                    session_id, cmd = parts[1], parts[2]
                    response = client.send_and_wait(f"meterpreter {session_id} {cmd}")
                    print(response)
            # Alex End
            elif message.lower() == "sliver_sessions":
                try:
                    output = subprocess.check_output("sliver-client sessions", shell=True, text=True)
                    print(f"{GREEN}[Sliver Sessions]\n{output}{RESET}")
                except Exception as e:
                    print(f"{RED}[Client] Error fetching Sliver sessions: {e}{RESET}")
            # Alex New

            else:
                response = client.send_and_wait(message)
                if "Please enter" in response:
                    while "Please enter" in response:
                        param_prompt = response.split("\n")[-1]  # Get last line for input
                        user_input = input(param_prompt + " ")
                        response = client.send_and_wait(user_input)
                # print(response)

    except KeyboardInterrupt:
        client.stop()
    finally:
        print(f"{GREEN}[Client] Stopped.{RESET}")

if __name__ == "__main__":
    main()