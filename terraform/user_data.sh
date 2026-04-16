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
if [ ! -d "career-agent" ]; then
  git clone ${github_repo} career-agent
fi
cd career-agent
git fetch origin
git checkout ${github_branch}
git pull origin ${github_branch}

# Create .env file with AWS resources
cat > .env << ENVEOF
DATABASE_URL=postgresql://${db_user}:${db_password}@${db_host}:${db_port}/${db_name}
CHROMA_HOST=${chroma_host}
CHROMA_PORT=${chroma_port}
AWS_REGION=${region}
NODE_ENV=production
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVEOF

echo "=== Building backend image ==="
cd backend
docker build -t career-agent-backend .

echo "=== Building frontend image ==="
cd ../frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t career-agent-frontend .

cd /home/ec2-user/career-agent

echo "=== Starting backend container ==="
docker run -d --name career-agent-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  career-agent-backend

echo "=== Starting frontend container ==="
docker run -d --name career-agent-frontend \
  --restart unless-stopped \
  -p 3000:3000 \
  career-agent-frontend

# Wait for services
sleep 30

echo "=== Checking service status ==="
docker ps
docker logs career-agent-backend --tail=50 || true
docker logs career-agent-frontend --tail=50 || true

echo "=== Testing services ==="
curl -s http://localhost:3000/ > /dev/null && echo "Frontend OK" || echo "Frontend FAILED"
curl -s http://localhost:8000/health > /dev/null && echo "Backend OK" || echo "Backend FAILED"

echo "=== User Data Script Completed at $(date) ==="
