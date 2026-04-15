output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS hostname"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Database master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_password" {
  description = "Database password - store securely; use for DATABASE_URL"
  value       = random_password.db.result
  sensitive   = true
}

# Example DATABASE_URL for the app (user must substitute password)
output "database_url_example" {
  description = "Example DATABASE_URL (replace PASSWORD with actual password)"
  value       = "postgresql://${aws_db_instance.main.username}:PASSWORD@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
}

# Full DATABASE_URL for .env (run: terraform output -raw database_url)
# Password is percent-encoded so % and @ in the password don't break the URL
output "database_url" {
  description = "Full PostgreSQL connection URL for DATABASE_URL in .env"
  value       = "postgresql://${aws_db_instance.main.username}:${local.db_password_encoded}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

# Chroma on EC2
output "chroma_host" {
  description = "Chroma server host (EC2 public IP). Set CHROMA_HOST to this for remote Chroma."
  value       = aws_instance.chroma.public_ip
}

output "chroma_url" {
  description = "Chroma server URL (http://host:8000)"
  value       = "http://${aws_instance.chroma.public_ip}:8000"
}

# Application Load Balancer
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

# Application Domain
output "app_url" {
  description = "Application URL"
  value       = "http://${var.app_domain}"
}

# Auto Scaling Group
output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.name
}

output "asg_min_size" {
  description = "Minimum size of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.min_size
}

output "asg_max_size" {
  description = "Maximum size of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.max_size
}
