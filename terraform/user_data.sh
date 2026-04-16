#!/bin/bash
exec > /var/log/user-data.log 2>&1
set -x

echo "=== User Data Script Started at $(date) ==="

# Update and install Docker
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

echo "=== Docker installed and started ==="

# Create simple HTML for frontend
mkdir -p /opt/app/frontend
cat > /opt/app/frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Career Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .status { padding: 15px; background: #e8f5e9; border-radius: 5px; margin: 20px 0; }
        .info { background: #f5f5f5; padding: 10px; border-left: 4px solid #2196F3; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>🚀 Career Agent</h1>
    <div class="status">
        <strong>Status:</strong> ✅ System is running
    </div>
    <div class="info">
        <strong>Frontend:</strong> Active<br>
        <strong>Backend API:</strong> <a href="/api/health">/api/health</a><br>
        <strong>Database:</strong> PostgreSQL 16 (${db_host})<br>
        <strong>Vector DB:</strong> Chroma (${chroma_host})
    </div>
    <p>Welcome to your Career Agent application!</p>
</body>
</html>
EOF

# Create simple backend API
mkdir -p /opt/app/backend
cat > /opt/app/backend/server.py << 'PYEOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "career-agent-api"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), SimpleHandler)
    print('Backend running on port 8000')
    server.serve_forever()
PYEOF

echo "=== Starting Frontend (nginx on port 3000) ==="
docker run -d --name frontend --restart always \
  -p 3000:80 \
  -v /opt/app/frontend:/usr/share/nginx/html:ro \
  nginx:alpine

echo "=== Starting Backend (python on port 8000) ==="
nohup python3 /opt/app/backend/server.py > /var/log/backend.log 2>&1 &

# Wait for services to start
sleep 10

echo "=== Testing services ==="
curl -s http://localhost:3000/ > /dev/null && echo "Frontend OK" || echo "Frontend FAILED"
curl -s http://localhost:8000/health > /dev/null && echo "Backend OK" || echo "Backend FAILED"

echo "=== User Data Script Completed at $(date) ==="
