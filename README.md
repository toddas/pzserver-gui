# Project Zomboid Server GUI Manager

A modern, web-based management interface for Project Zomboid dedicated servers (LinuxGSM). Built with Flask, Jinja2, and TailwindCSS.

<img width="1079" height="1319" alt="image" src="https://github.com/user-attachments/assets/11fc3043-8750-437d-9151-dbd2e3f3755d" />


## Features
- **Server Control**: Start, Stop, Restart, and view details of your PZ Server.
- **Mod Management**: Easily add Workshop mods. The app automatically updates `server.ini` with Mod IDs and Workshop IDs.
- **Sandbox Editor**: Edit `SandboxVars.lua` with a user-friendly form.
- **Config Editor**: Edit general server settings (`server.ini`).
- **Security**: Password sanitization in logs.

---

## � Local Development (Docker)

Use Docker to run the application locally with **mock data**. This allows you to develop or test the UI without affecting a live server.

### Prerequisites
- Docker Engine & Docker Compose

### 1. Clone the repository
```bash
git clone https://github.com/toddas/pzserver-gui.git
cd pzserver-gui
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```
The application will be available at **http://localhost:5000**.
*Note: This environment uses mock files located in `mock/`. Changes here will not affect a real server.*

### 3. (Optional) Windows LGE Fix
If you cloned the repo on Windows but plan to run it in a Linux Docker container, run this to fix line endings for the mock script:
```bash
sed -i 's/\r$//' mock/pzserver_script 
```

---

## � Production Installation (Linux/VPS)

To run the manager on your actual Project Zomboid server (alongside LinuxGSM).

### 1. Automated Setup
We provide a script to set up the user, permissions, and service automatically.

```bash
cd server_files
chmod +x easysetup.sh
sudo ./easysetup.sh
```

### 2. Manual Setup
If you want to configure it yourself:

1.  **Install Dependencies**:
    ```bash
    sudo apt update && sudo apt install python3 python3-pip
    pip3 install -r requirements.txt
    ```

2.  **Configure Sudoers**:
    The service needs to run LinuxGSM commands as the `pzserver` user.
    ```bash
    # Add to /etc/sudoers.d/pzserver
    pzserver ALL=(pzserver) NOPASSWD: ALL
    ```

3.  **Run the App**:
    ```bash
    python3 run.py
    ```
    *Note: For production, use Gunicorn or a systemd service (template provided in `server_files/pzserver-gui.service`).*

---

## 📂 Project Structure

```
pzserver-gui/
├── app/                 # Flask Application Logic
│   ├── routes/          # API & Frontend Routes
│   ├── services/        # Server & File Management Logic
│   └── utils/           # Parsers & Helpers
├── server_files/        # Setup scripts & Service templates
├── static/              # CSS & JavaScript
├── templates/           # HTML Templates (Jinja2)
├── run.py               # Entry Point
└── Dockerfile           # Docker Configuration
```

## 🔐 Security Note
- **Secret Key**: In production, ensure you set the `SECRET_KEY` environment variable.
- **Gitignore**: The `.gitignore` is configured to exclude `server_files/` (the directory where the setup script might copy sensitive data if executed there) and other secrets. **Do not commit your actual server.ini or database files.**

## License
MIT
