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

# Install pymetasploit3
RUN pip install pymetasploit3

# Set the default shell to Bash
#SHELL ["/bin/bash", "-c"]

# Install pymetasploit3
RUN pip install pymetasploit3

# Install Metasploit
RUN git clone https://github.com/rapid7/metasploit-framework.git /opt/metasploit-framework && \
    cd /opt/metasploit-framework && \
    git submodule init && \
    git submodule update && \
    gem install bundler && \
    bundle install

ENV PATH="/opt/metasploit-framework/:$PATH"

# Run the msfconsole.rc commands and start Metasploit RPC service
COPY ./src/config_files/msfconsole.rc /opt/metasploit-framework/msfconsole.rc

# Install Sliver-py
RUN pip install sliver-py

# Sliver Client and Sliver Server

RUN wget https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-client_linux

RUN wget https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-server_linux

RUN chmod +x sliver-client_linux sliver-server_linux && \
    mv sliver-client_linux /usr/local/bin/sliver-client && \
    mv sliver-server_linux /usr/local/bin/sliver-server

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
EXPOSE 80 4444 8080 55552 55553

#start the start.sh script
# CMD ["/bin/bash", "-c", "/workspace/enderCLI/start.sh"]

# Set entrypoint for debugging and interactive use
ENTRYPOINT ["/bin/bash", "-i"]


