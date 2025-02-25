import socket
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
            message = input(f"{GREEN}Enter message (or 'quit' to exit): {RESET}")
            if message.lower() == 'quit':
                client.stop()
                break
            response = client.send_and_wait(message)
            # Response is printed in receive_messages, but you can reuse it here if needed
    except KeyboardInterrupt:
        client.stop()
    finally:
        print(f"{GREEN}[Client] Stopped.{RESET}")

if __name__ == "__main__":
    main()