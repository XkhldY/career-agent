terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  # Uncomment and set for remote state (e.g. S3)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "recruitment/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# VPC and subnets for RDS (RDS requires at least 2 AZs in the subnet group)
# ---------------------------------------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  subnet_ids          = slice(tolist(data.aws_subnets.default.ids), 0, min(2, length(data.aws_subnets.default.ids)))
  db_password_encoded = replace(replace(random_password.db.result, "%", "%25"), "@", "%40")
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = local.subnet_ids
  tags = {
    Project = var.project_name
  }
}

# ---------------------------------------------------------------------------
# Security group for RDS
# ---------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow PostgreSQL access for recruitment app"
  vpc_id      = data.aws_vpc.default.id
  tags = {
    Project = var.project_name
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_postgres" {
  security_group_id = aws_security_group.rds.id
  cidr_ipv4        = "0.0.0.0/0"
  from_port        = 5432
  to_port          = 5432
  ip_protocol      = "tcp"
  description      = "PostgreSQL from allowed CIDRs"
}

# ---------------------------------------------------------------------------
# Random password for RDS (store in Secrets Manager in production)
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 24
  special = false
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL instance
# ---------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result
  port     = 5432

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = true # Set false and use private subnets in production

  skip_final_snapshot       = true
  backup_retention_period   = 7
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:04:00-sun:05:00"
  multi_az                  = false
  deletion_protection       = false

  tags = {
    Project = var.project_name
  }
}
