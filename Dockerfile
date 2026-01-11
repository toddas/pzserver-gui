FROM python:3.9-slim

# Install sudo (required to mimic the production environment)
RUN apt-get update && apt-get install -y sudo && rm -rf /var/lib/apt/lists/*

# 1. Create the 'pzserver' user and group
RUN useradd -m -s /bin/bash pzserver

# 2. Create directory structure mimicking Project Zomboid
RUN mkdir -p /home/pzserver/server \
    && mkdir -p /home/pzserver/Zomboid/Server \
    && mkdir -p /home/pzserver/Zomboid/Saves/Multiplayer/servertest

WORKDIR /app
RUN pip install Flask

# 3. Copy Application Files
# (Added sandbox.html to the list)
# 3. Copy Application Files
COPY run.py ./
COPY app ./app
COPY templates ./templates
COPY static ./static
COPY favicon.ico ./static/favicon.ico

# 4. Copy Mock Configuration Files
COPY mock/pzserver_script /home/pzserver/server/pzserver
COPY mock/pzserver.ini /home/pzserver/Zomboid/Server/pzserver.ini
COPY mock/pzserver_SandboxVars.lua /home/pzserver/Zomboid/Server/pzserver_SandboxVars.lua

# 5. [NEW] Create Dummy Data for Reset Testing
# Create fake files so "Soft Reset" has something to delete
RUN touch /home/pzserver/Zomboid/Saves/Multiplayer/servertest/map_t.bin \
    && touch /home/pzserver/Zomboid/Saves/Multiplayer/servertest/zpop_virtual.bin \
    && touch /home/pzserver/Zomboid/Saves/Multiplayer/servertest/players.db

# 6. [NEW] Ensure pzserver.ini has a ResetID for testing
# This appends ResetID if it's missing, so Hard Reset logic can be tested
RUN echo "\nResetID=12345678" >> /home/pzserver/Zomboid/Server/pzserver.ini

# 7. Set Permissions
RUN chmod +x /home/pzserver/server/pzserver
# Ensure pzserver user owns ALL the mock directories and files
RUN chown -R pzserver:pzserver /home/pzserver

# 8. Configure Sudo for the mock user
RUN echo "root ALL=(pzserver) NOPASSWD: ALL" > /etc/sudoers.d/pzserver

# 9. Set Environment Variable
ENV PZ_ENV=local

EXPOSE 5000

CMD ["python", "run.py"]