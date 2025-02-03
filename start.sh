#!/bin/bash
echo "Starting Operator Container..."

# Wait until Docker is fully running
until docker info >/dev/null 2>&1; do
    echo "Waiting for Docker to start..."
    sleep 3
done

echo "Docker is ready. Launching server and client containers..."

# Remove old containers if they exist
docker rm -f server client >/dev/null 2>&1

# Run the server inside the operator container
docker run -d --name server --network localnet --ip 10.1.1.4 my_server_image

# Run the client inside the operator container
docker run -d --name client --network localnet --ip 10.1.1.5 my_client_image

echo "Server and Client started successfully!"

# Keep the container running
exec tail -f /dev/null
