#!/bin/bash

# ==============================================================================
# PROJECT ZOMBOID SERVER MANAGER - AUTO INSTALLER
# ==============================================================================
# This script sets up the Project Zomboid server using LinuxGSM and installs
# the Python Flask Web GUI service.
#
# USAGE: sudo ./setup.sh
# ==============================================================================

# --- CONFIGURATION ---
PZ_USER="pzserver"
PZ_HOME="/home/$PZ_USER"
SERVER_DIR="$PZ_HOME/server"
GUI_DIR="$PZ_HOME/webgui-flask"
SERVICE_NAME="pzserver-manager"

# Detect script directory and repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Please run as root (sudo ./setup.sh)${NC}"
  exit 1
fi

echo -e "${GREEN}>>> STARTING INSTALLATION...${NC}"

# ------------------------------------------------------------------------------
# 1. SYSTEM UPDATE & DEPENDENCIES
# ------------------------------------------------------------------------------
echo -e "${GREEN}>>> [1/6] Updating system and installing dependencies...${NC}"
apt-get update
# Dependencies for LinuxGSM and Python/Flask
apt-get install -y curl wget file tar bzip2 gzip unzip bsdmainutils python3 util-linux ca-certificates binutils bc jq tmux netcat lib32gcc-s1 lib32stdc++6 python3-pip git sudo

# ------------------------------------------------------------------------------
# 2. USER CREATION
# ------------------------------------------------------------------------------
echo -e "${GREEN}>>> [2/6] Setting up user '$PZ_USER'...${NC}"
if id "$PZ_USER" &>/dev/null; then
    echo -e "${YELLOW}User $PZ_USER already exists. Skipping creation.${NC}"
else
    useradd -m -s /bin/bash $PZ_USER
    passwd -d $PZ_USER # Remove password (access via root or ssh keys)
    echo "User $PZ_USER created."
fi

# ------------------------------------------------------------------------------
# 3. SUDOERS CONFIGURATION (Critical for Web GUI)
# ------------------------------------------------------------------------------
# Allows the 'pzserver' user to run specific commands as itself via sudo without password.
# This fixes the "sudo: a terminal is required" error in the Flask app.
echo -e "${GREEN}>>> [3/6] Configuring sudoers for passwordless execution...${NC}"
SUDO_CONF="/etc/sudoers.d/$PZ_USER"
if ! grep -q "$PZ_USER ALL=($PZ_USER) NOPASSWD: ALL" "$SUDO_CONF" 2>/dev/null; then
    echo "$PZ_USER ALL=($PZ_USER) NOPASSWD: ALL" > "$SUDO_CONF"
    chmod 0440 "$SUDO_CONF"
    echo "Sudoers updated."
else
    echo -e "${YELLOW}Sudoers already configured.${NC}"
fi

# ------------------------------------------------------------------------------
# 4. LINUXGSM INSTALLATION (Project Zomboid Server)
# ------------------------------------------------------------------------------
echo -e "${GREEN}>>> [4/6] Installing LinuxGSM (pzserver)...${NC}"
sudo -u $PZ_USER mkdir -p $SERVER_DIR

if [ ! -f "$SERVER_DIR/pzserver" ]; then
    echo "Downloading LinuxGSM script..."
    cd $SERVER_DIR
    sudo -u $PZ_USER wget -O linuxgsm.sh https://linuxgsm.sh
    sudo -u $PZ_USER chmod +x linuxgsm.sh
    sudo -u $PZ_USER bash linuxgsm.sh pzserver
    
    echo -e "${YELLOW}NOTE: You may need to manually complete the install if it asks for Steam credentials.${NC}"
    echo "Attempting auto-install..."
    sudo -u $PZ_USER ./pzserver auto-install
else
    echo -e "${YELLOW}LinuxGSM is already installed in $SERVER_DIR.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. WEB GUI INSTALLATION
# ------------------------------------------------------------------------------
echo -e "${GREEN}>>> [5/6] Deploying Web GUI Manager...${NC}"

# Create directory
sudo -u $PZ_USER mkdir -p $GUI_DIR

# Copy files from current directory (where setup.sh is run) to target
# We exclude setup.sh itself and hidden git files
echo "Copying application files..."
# We exclude server_files (scripts), hidden git files, and dev config
echo "Copying application files..."
rsync -av --progress "$REPO_ROOT/" "$GUI_DIR" --exclude server_files --exclude .git --exclude .gitignore --exclude .env

# Set ownership
chown -R $PZ_USER:$PZ_USER $GUI_DIR

# Install Python Requirements
echo "Installing Python dependencies..."
if [ -f "$GUI_DIR/requirements.txt" ]; then
    echo "Found requirements.txt. Installing..."
    # Installing globally for simplicity on the server, or use venv if preferred
    pip3 install -r "$GUI_DIR/requirements.txt"
else
    echo -e "${YELLOW}requirements.txt not found. Installing Flask manually...${NC}"
    pip3 install flask
fi

# ------------------------------------------------------------------------------
# 6. SYSTEMD SERVICE SETUP
# ------------------------------------------------------------------------------
echo -e "${GREEN}>>> [6/6] Configuring Systemd Service...${NC}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cat > $SERVICE_FILE <<EOF
[Unit]
Description=Project Zomboid Server Manager API
After=network.target

[Service]
User=$PZ_USER
WorkingDirectory=$GUI_DIR
ExecStart=/usr/bin/python3 run.py
Restart=always
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

# Reload and Enable
echo "Reloading systemd daemon..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
echo "Restarting service..."
systemctl restart $SERVICE_NAME

# ------------------------------------------------------------------------------
# COMPLETION
# ------------------------------------------------------------------------------
IP_ADDR=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN} INSTALLATION COMPLETE! ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Web GUI is active at:  ${YELLOW}http://$IP_ADDR:5000${NC}"
echo -e "Server Directory:      $SERVER_DIR"
echo -e "GUI Directory:         $GUI_DIR"
echo -e "Service Status:        sudo systemctl status $SERVICE_NAME"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC} If you used 'requirements.txt', ensure it didn't contain"
echo -e "Windows-specific packages (like pywin32) if you generated it on Windows."
echo -e "If the service fails to start, check logs with: journalctl -u $SERVICE_NAME -f"