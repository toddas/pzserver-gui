## local-dev:

### prerequisites:
You need **Docker Engine** and **Docker Compose** installed to run the application.

#### Linux (Ubuntu/Debian)
1.  **Install Docker Engine & Compose Plugin:**
    ```bash
    # Update and install dependencies
    sudo apt update && sudo apt install ca-certificates curl gnupg
    # Add Docker's GPG key and repository
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL [https://download.docker.com/linux/ubuntu/gpg](https://download.docker.com/linux/ubuntu/gpg) | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] [https://download.docker.com/linux/ubuntu](https://download.docker.com/linux/ubuntu) $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    # Install Docker and Compose V2 plugin
    sudo apt update
    sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin
    # Recommended: Add user to the docker group (log out/in required)
    sudo usermod -aG docker $USER
    ```
2.  **Verify:** Run `docker run hello-world` and `docker compose version`.

#### Windows
1.  **Install Docker Desktop:** Download and install **Docker Desktop** from the official website (it includes Docker Engine and Docker Compose V2).
2.  **Ensure WSL 2 is enabled** (recommended during install).
3.  **Start Docker Desktop** before proceeding.
4.  **Verify:** Open PowerShell/CMD and run `docker --version` and `docker compose version`.

### setup:
This setup assumes you are using a terminal (Git Bash, PowerShell, or Command Prompt) on Windows, or any terminal on Linux.

#### Linux & Windows
```
git clone git@github.com:toddas/pzserver-gui.git 
cd pzserver-gui 
docker compose build 
docker compose up
```
