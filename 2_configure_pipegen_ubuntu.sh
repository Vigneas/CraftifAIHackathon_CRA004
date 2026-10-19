#!/bin/bash
set -e

echo "=========================================================="
echo " CraftifAI PipeGen Ubuntu Configuration Script"
echo "=========================================================="

# 1. Update apt repositories
echo "[+] Updating apt repositories..."
sudo apt-get update -y

# 2. Install socat and essential utilities
echo "[+] Installing socat, curl, gnupg, lsb-release..."
sudo apt-get install -y socat curl gnupg lsb-release ca-certificates

# 3. Check for PipeGen prerequisite script from CraftifAI
if [ -f "./pipegen_prerequisites_ubuntu_x86.sh" ]; then
    echo "[+] Found official pipegen_prerequisites_ubuntu_x86.sh! Executing..."
    chmod +x ./pipegen_prerequisites_ubuntu_x86.sh
    ./pipegen_prerequisites_ubuntu_x86.sh
else
    echo "[+] Installing Docker and NVIDIA Container Toolkit manually as per guide..."
    
    # Install Docker
    sudo install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.asc ]; then
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
    fi
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker $USER

    # Install NVIDIA Container Toolkit
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update -y
    sudo apt-get install -y nvidia-container-toolkit

    # Configure Docker for NVIDIA
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker || sudo service docker restart
fi

# 4. Check for PipeGen debian package
DEB_FILE=$(ls PipeGen_*.deb 2>/dev/null | head -n 1)
if [ -n "$DEB_FILE" ]; then
    echo "[+] Installing PipeGen package: $DEB_FILE..."
    sudo dpkg -i "$DEB_FILE"
    echo "[+] PipeGen installed successfully! Run 'pipegen' to launch."
else
    echo "[!] No PipeGen_*.deb found in the current directory."
    echo "[!] Please copy your downloaded PipeGen deb package here and run: sudo dpkg -i <filename>.deb"
fi

echo "=========================================================="
echo " Setup complete! If you added your user to the docker"
echo " group, run 'newgrp docker' or reopen your shell."
echo "=========================================================="
