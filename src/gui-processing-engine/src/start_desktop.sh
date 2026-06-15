#!/bin/bash
set -e

# 1. Start X Virtual Framebuffer (Xvfb) on DISPLAY :99 with OpenGL GLX support
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 +extension GLX +render -noreset &
sleep 1

# 2. Start Openbox Window Manager (handles window borders and moving)
openbox-session &

# 3. Start x11vnc to capture the Xvfb screen
x11vnc -display :99 -nopw -forever -shared -bg -xkb

# 4. Start Websockify to bridge VNC (tcp:5900) to WebSockets
# noVNC client will connect to this WebSocket port
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &

# 5. Start the internal API Server (Port 8080) to receive user code
# This server is responsible for saving the code and executing it on DISPLAY :99
python3 /app/gui_server.py
