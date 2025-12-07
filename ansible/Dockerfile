# Use Ubuntu as the base image
FROM ubuntu:latest

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install required software
RUN apt-get update && apt-get install -y \
    openssh-server \
    python3 \
    && apt-get clean

# Set the root password to "root@123"
RUN echo "root:root@123" | chpasswd

# Allow root login and enable password authentication for SSH
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Expose SSH port
EXPOSE 22

# Ensure SSH runs on container startup
RUN update-rc.d ssh defaults

# Start SSH service and keep container running
CMD service ssh start && /bin/bash
