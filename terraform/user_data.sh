#!/bin/bash
set -e

# Enable detailed logging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting user data script at $(date)"

# Update system
yum update -y
yum install -y git docker docker-compose nodejs npm python3 python3-pip curl wget

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone the repository
cd /home/ec2-user
git clone ${github_repo} agentics
cd agentics
git checkout ${github_branch}

# Create .env file with AWS connection details
cat > .env << 'EOF'
# Database
DATABASE_URL="postgresql://${db_user}:${db_password}@${db_host}:${db_port}/${db_name}?sslmode=require"

# Chroma Vector Database
CHROMA_HOST="${chroma_host}"
CHROMA_PORT="${chroma_port}"

# AWS
AWS_REGION="${region}"

# Application
NODE_ENV="production"
NEXT_PUBLIC_API_URL="http://$(hostname -f):8001"
EOF

# Build and start Docker Compose
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Create a health check endpoint script
cat > /home/ec2-user/health_check.sh << 'HEALTH_EOF'
#!/bin/bash
# Simple health check endpoint
echo "OK"
HEALTH_EOF

chmod +x /home/ec2-user/health_check.sh

# Set up a simple HTTP health check handler on port 80
cat > /etc/systemd/system/health-check.service << 'SERVICE_EOF'
[Unit]
Description=Health Check HTTP Server
After=docker.service

[Service]
Type=simple
User=ec2-user
ExecStart=/usr/bin/python3 -m http.server 80 --directory /home/ec2-user
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable and start health check service
systemctl daemon-reload
systemctl enable health-check.service
systemctl start health-check.service

echo "User data script completed at $(date)"
