# Stage 2: Ender-Specific Layer
FROM ubuntu:22.04 AS ender

# Set the non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install necessary packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip vim nano curl wget bash nmap netcat \
    hydra ruby ruby-dev build-essential iproute2 net-tools\
    openssl libreadline-dev zlib1g-dev libpcap-dev git \
    lsb-release software-properties-common \
    iputils-ping iputils-tracepath iputils-arping dnsutils \
    openssh-server ruby-full libssl-dev \
    libsqlite3-dev libpq-dev libyaml-dev \
    libxml2-dev libxslt1-dev \
    mingw-w64 binutils-mingw-w64 g++-mingw-w64 mingw-w64-tools gcc-mingw-w64 \ 
    libcurl4-openssl-dev libgmp-dev sudo libffi-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set Python3 as the default Python command
RUN ln -sf python3 /usr/bin/python

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


