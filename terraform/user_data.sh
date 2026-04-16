#!/bin/bash
exec > /var/log/user-data.log 2>&1
set -x

echo "=== User Data Script Started at $(date) ==="

# Update and install dependencies
yum update -y
yum install -y docker git

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

echo "=== Docker installed and started ==="

# Clone the repository
cd /home/ec2-user
git clone ${github_repo} app || echo "Clone failed, trying cached"
cd app || exit 1
git checkout ${github_branch} || echo "Checkout failed"

# Create .env file with AWS resources
cat > .env << EOF
# Database
DATABASE_URL=postgresql://${db_user}:${db_password}@${db_host}:${db_port}/${db_name}

# Chroma Vector Database
CHROMA_HOST=${chroma_host}
CHROMA_PORT=${chroma_port}

# AWS
AWS_REGION=${region}

# Application
NODE_ENV=production
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

echo "=== Building backend image ==="
cd backend
docker build -t agentics-backend . || echo "Backend build failed"

echo "=== Building frontend image ==="
cd ../frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t agentics-frontend . || echo "Frontend build failed"

cd /home/ec2-user/app

echo "=== Starting backend container ==="
docker run -d --name backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  agentics-backend || echo "Backend start failed"

echo "=== Starting frontend container ==="
docker run -d --name frontend \
  --restart unless-stopped \
  -p 3000:3000 \
  agentics-frontend || echo "Frontend start failed"

# Wait for services
sleep 30

echo "=== Checking service status ==="
docker ps
docker logs backend --tail=50
docker logs frontend --tail=50

echo "=== Testing services ==="
curl -s http://localhost:3000/ > /dev/null && echo "Frontend OK" || echo "Frontend FAILED"
curl -s http://localhost:8000/health > /dev/null && echo "Backend OK" || echo "Backend FAILED"

echo "=== User Data Script Completed at $(date) ==="
