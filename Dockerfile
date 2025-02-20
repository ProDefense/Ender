# Stage 2: Ender-Specific Layer
FROM eshu:latest

# Set working directory for Ender
WORKDIR /workspace/enderCLI

# Copy Ender’s source code into the container
COPY ./src/ /workspace/enderCLI/
COPY ./eshu/ /workspace/enderCLI/

# Copy startup script into the container
COPY ./start.sh /workspace/enderCLI/start.sh
RUN chmod +x /workspace/enderCLI/start.sh

# Install Ender-specific dependencies (if any)
RUN python3 -m pip install --upgrade pip setuptools
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Optionally add Ender-specific tools
RUN apt-get update && apt-get install -y \
    # Add tools here, e.g., sqlmap, john, etc.
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to include the Eshu module
ENV PYTHONPATH="/workspace/ender/eshu/src:$PYTHONPATH"

# Expose Ender-specific ports
EXPOSE 1337 8081

#start the start.sh script
# CMD ["/bin/bash", "-c", "/workspace/enderCLI/start.sh"]

# Set entrypoint for debugging and interactive use
ENTRYPOINT ["/bin/bash", "-i"]


