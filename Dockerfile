FROM python:3.9-slim

# Install sudo (required to mimic the production environment)
RUN apt-get update && apt-get install -y sudo && rm -rf /var/lib/apt/lists/*

# 1. Create the 'pzserver' user and group
RUN useradd -m -s /bin/bash pzserver

RUN mkdir -p /home/pzserver/server \
    && mkdir -p /home/pzserver/Zomboid/Server


WORKDIR /app
RUN pip install Flask

COPY main.py utils.py ./
COPY index.html mods.html  ./
COPY script.js favicon.ico style.css ./

COPY mock/pzserver_script /home/pzserver/server/pzserver
COPY mock/pzserver.ini /home/pzserver/Zomboid/Server/pzserver.ini
COPY mock/pzserver_SandboxVars.lua /home/pzserver/Zomboid/Server/pzserver_SandboxVars.lua

# 6. Set Permissions
RUN chmod +x /home/pzserver/server/pzserver
RUN chown -R pzserver:pzserver /home/pzserver

# 7. Configure Sudo for the mock user
RUN echo "root ALL=(pzserver) NOPASSWD: ALL" > /etc/sudoers.d/pzserver

# 8. Set Environment Variable to force Local Mode in main.py
ENV PZ_ENV=local

EXPOSE 5000

CMD ["python", "main.py"]