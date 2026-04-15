variable "aws_region" {
  description = "AWS region for RDS and related resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "recruitment"
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "recruitment"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "recruitment_admin"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect to RDS (e.g. your IP or VPC CIDR)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict this in production
}

variable "chroma_data_path" {
  description = "Path for Chroma data (used in app when running Chroma locally)"
  type        = string
  default     = "data/chroma_db"
}

variable "chroma_instance_type" {
  description = "EC2 instance type for Chroma server"
  type        = string
  default     = "t3.small"
}

# Application variables
variable "app_instance_type" {
  description = "EC2 instance type for application servers"
  type        = string
  default     = "t3.small"
}

variable "asg_min_size" {
  description = "Minimum number of instances in Auto Scaling Group"
  type        = number
  default     = 2
}

variable "asg_max_size" {
  description = "Maximum number of instances in Auto Scaling Group"
  type        = number
  default     = 4
}

variable "asg_desired_capacity" {
  description = "Desired number of instances in Auto Scaling Group"
  type        = number
  default     = 2
}

variable "domain_name" {
  description = "Domain name (hosted zone in Route53)"
  type        = string
  default     = "pom100.com"
}

variable "app_domain" {
  description = "Application subdomain"
  type        = string
  default     = "career.pom100.com"
}

variable "github_repo" {
  description = "GitHub repository URL for the application"
  type        = string
  default     = "https://github.com/khaled/agentics.git"
}

variable "github_branch" {
  description = "GitHub branch to deploy"
  type        = string
  default     = "main"
}
