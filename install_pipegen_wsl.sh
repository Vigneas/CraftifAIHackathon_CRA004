#!/bin/bash
set -e

echo "=========================================================="
echo " PipeGen Complete Automated Installer for WSL2"
echo "=========================================================="

# 1. Create developer user if not exists
if ! id "developer" &>/dev/null; then
    echo "[+] Creating 'developer' user..."
    useradd -m -s /bin/bash -G sudo developer
    echo "developer ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/developer
    chmod 0440 /etc/sudoers.d/developer
fi

# Set default user in /etc/wsl.conf
if ! grep -q "default=developer" /etc/wsl.conf 2>/dev/null; then
    cat <<EOF >> /etc/wsl.conf
[user]
default=developer
[boot]
systemd=true
EOF
fi

# 2. Update apt and install essential tools
echo "[+] Installing socat, curl, ca-certificates, gnupg, zstd..."
apt-get update -y
apt-get install -y socat curl gnupg lsb-release ca-certificates zstd x11-utils libgl1-mesa-glx

# 3. Install Docker Engine
echo "[+] Installing Docker Engine..."
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add developer user to docker group
usermod -aG docker developer

# 4. Install NVIDIA Container Toolkit
echo "[+] Installing NVIDIA Container Toolkit..."
if [ ! -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg ]; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
fi

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' > \
  /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update -y
apt-get install -y nvidia-container-toolkit

# Configure Docker daemon for NVIDIA runtime
echo "[+] Configuring Docker daemon with NVIDIA Container Toolkit..."
nvidia-ctk runtime configure --runtime=docker

# Start Docker service
service docker restart || systemctl restart docker

# 5. Install PipeGen Package
DEB_PATH="/mnt/d/Bangalore 4.0/PipeGen_0.5.1_amd64.deb"
if [ -f "$DEB_PATH" ]; then
    echo "[+] Installing PipeGen package from: $DEB_PATH..."
    dpkg -i "$DEB_PATH" || apt-get install -f -y
    
    # Ensure /opt/PipeGen permissions as per guide
    if [ -d "/opt/PipeGen" ]; then
        chown -R developer:developer /opt/PipeGen
        chmod -R 775 /opt/PipeGen
    fi
    
    # Ensure ~/.pipegen exists and owned by developer
    mkdir -p /home/developer/.pipegen
    chown -R developer:developer /home/developer/.pipegen
    
    echo "[+] PipeGen installed successfully!"
else
    echo "[!] Warning: $DEB_PATH not found."
fi

echo "=========================================================="
echo " PipeGen WSL2 Installation Complete!"
echo "=========================================================="
