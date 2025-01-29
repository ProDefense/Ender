# Stage 1: Base Image with Eshu Setup
FROM ubuntu:22.04 AS eshu-base

# Set the non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install necessary packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip vim nano curl wget bash nmap netcat \
    hydra ruby ruby-dev build-essential iproute2 net-tools \
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

# Set the default shell to Bash
SHELL ["/bin/bash", "-c"]

# Increase Git buffer size to handle large repositories
RUN git config --global http.postBuffer 104857600

# Install pymetasploit3
RUN pip install pymetasploit3

# Install Metasploit Framework
RUN git clone --depth 1 https://github.com/rapid7/metasploit-framework.git /opt/metasploit-framework && \
    cd /opt/metasploit-framework && \
    git submodule init && \
    git submodule update --depth 1 && \
    gem install bundler && \
    bundle install

ENV PATH="/opt/metasploit-framework/:$PATH"

# Copy custom Metasploit RC file
COPY ./eshu/src/config_files/msfconsole.rc /opt/metasploit-framework/msfconsole.rc

# Install Sliver-py
RUN pip install sliver-py

# Install Sliver binaries
RUN wget https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-client_linux && \
    wget https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-server_linux && \
    chmod +x sliver-client_linux sliver-server_linux && \
    mv sliver-client_linux /usr/local/bin/sliver-client && \
    mv sliver-server_linux /usr/local/bin/sliver-server

# Set up working directory for Eshu
WORKDIR /workspace/eshuCLP
COPY ./eshu/src/ /workspace/eshuCLP/

# Install dependencies from pyproject.toml in Eshu
COPY ./eshu/src/pyproject.toml /workspace/eshuCLP/
RUN python3 -m pip install --upgrade pip setuptools && \
    pip install .

# Stage 2: Ender-Specific Layer
FROM eshu-base AS ender

# Set working directory for Ender
WORKDIR /workspace/ender

# Copy Ender’s source code into the container
COPY ./src/ /workspace/ender/

# Expose Ender-specific ports
EXPOSE 1337 8081

# Set entrypoint for debugging and interactive use
ENTRYPOINT ["/bin/bash", "-i"]
