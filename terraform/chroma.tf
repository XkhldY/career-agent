# ---------------------------------------------------------------------------
# Chroma on EC2: single instance with Docker, data on root volume
# ---------------------------------------------------------------------------

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_security_group" "chroma" {
  name        = "${var.project_name}-chroma-sg"
  description = "Chroma server on port 8000"
  vpc_id      = data.aws_vpc.default.id
  tags = {
    Project = var.project_name
  }
}

resource "aws_vpc_security_group_ingress_rule" "chroma_8000" {
  security_group_id = aws_security_group.chroma.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 8000
  to_port           = 8000
  ip_protocol       = "tcp"
  description       = "Chroma HTTP API"
}

resource "aws_vpc_security_group_ingress_rule" "chroma_ssh" {
  security_group_id = aws_security_group.chroma.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  description       = "SSH for debugging"
}

resource "aws_vpc_security_group_egress_rule" "chroma_all" {
  security_group_id = aws_security_group.chroma.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Allow all outbound"
}

locals {
  chroma_user_data = <<-EOT
#!/bin/bash
set -e
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
mkdir -p /opt/chroma_data
docker run -d --name chroma --restart unless-stopped \
  -p 8000:8000 -v /opt/chroma_data:/data \
  -e IS_PERSISTENT=TRUE -e ANONYMIZED_TELEMETRY=FALSE \
  chromadb/chroma:latest
EOT
}

resource "aws_instance" "chroma" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.chroma_instance_type
  vpc_security_group_ids = [aws_security_group.chroma.id]
  subnet_id              = local.subnet_ids[0]
  user_data              = local.chroma_user_data
  tags = {
    Project = var.project_name
    Name    = "${var.project_name}-chroma"
  }
}
