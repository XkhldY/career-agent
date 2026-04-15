# AWS Deployment Guide

This guide covers deploying the Agentics application to AWS with:
- **EC2 Auto Scaling Group** for the backend and frontend
- **RDS PostgreSQL** for the database
- **Chroma** vector database on EC2
- **Application Load Balancer** for traffic distribution
- **Route53** DNS configuration for career.pom100.com

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** installed (>= 1.0)
4. **Git** installed
5. **GitHub personal access token** (if the repo is private)
6. **Domain** (pom100.com) configured in Route53

## Step 1: Prepare Route53 Domain

Before deploying, ensure your domain is set up in Route53:

```bash
# Check if hosted zone exists
aws route53 list-hosted-zones-by-name --dns-name pom100.com

# If not, create it
aws route53 create-hosted-zone --name pom100.com --caller-reference $(date +%s)
```

## Step 2: Configure Terraform Variables

Edit `terraform/variables.tf` to customize:

```bash
cd terraform

# Override variables if needed
cat > terraform.tfvars << EOF
aws_region                = "us-east-1"
project_name              = "recruitment"
app_instance_type         = "t3.small"
asg_min_size              = 2
asg_max_size              = 4
asg_desired_capacity      = 2
domain_name               = "pom100.com"
app_domain                = "career.pom100.com"
github_repo               = "https://github.com/yourusername/agentics.git"
github_branch             = "main"
EOF
```

## Step 3: Initialize Terraform

```bash
cd terraform
terraform init
```

This creates the `.terraform` directory and downloads the AWS provider.

## Step 4: Validate and Plan

```bash
# Validate configuration
terraform validate

# Plan the deployment (shows what will be created)
terraform plan
```

Review the plan to ensure everything looks correct.

## Step 5: Deploy Infrastructure

```bash
# Make the deploy script executable
chmod +x ../scripts/deploy.sh

# Run the deployment
../scripts/deploy.sh
```

The script will:
1. Validate your AWS credentials
2. Initialize Terraform
3. Create a deployment plan
4. Ask for confirmation
5. Apply the configuration
6. Display outputs

This process typically takes **15-20 minutes**.

## Step 6: Verify Deployment

```bash
# Make the verification script executable
chmod +x ../scripts/verify-deployment.sh

# Run verification checks
../scripts/verify-deployment.sh
```

This checks:
- PostgreSQL database connectivity
- Chroma vector database availability
- Application Load Balancer status

## Step 7: Monitor Application Startup

After deployment, EC2 instances need time to:
1. Boot
2. Install Docker and dependencies
3. Clone your repository
4. Build Docker images
5. Start containers

**Expected startup time: 5-10 minutes**

Monitor instance initialization:

```bash
# Get Auto Scaling Group instances
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names recruitment-asg \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus]'

# SSH into an instance
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names recruitment-asg \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

aws ec2-instance-connect open-tunnel --instance-id $INSTANCE_ID

# Then SSH
ssh -i your-key-pair.pem ec2-user@<instance-public-ip>
```

## Step 8: Check Application Status

Once instances are running:

```bash
# SSH into instance and check Docker
docker-compose ps

# View logs
docker-compose logs -f

# Check specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Step 9: Access Your Application

### Via ALB DNS (immediately available)
```
Frontend: http://<ALB-DNS>:3000
Backend: http://<ALB-DNS>:8000
```

### Via Route53 Domain (after propagation)
```
Frontend: http://career.pom100.com:3000
Backend: http://career.pom100.com:8000
```

Get the ALB DNS from outputs:
```bash
cd terraform
terraform output alb_dns_name
```

## Troubleshooting

### EC2 instances not starting
```bash
# Check instance status
aws ec2 describe-instance-status --instance-ids <instance-id>

# View system logs
aws ec2 get-console-output --instance-id <instance-id>
```

### Docker containers not running
```bash
# SSH into instance and check
docker-compose ps
docker-compose logs

# Restart services
docker-compose restart
```

### Database connection issues
```bash
# Verify security group allows access
aws ec2 describe-security-groups --group-names recruitment-rds-sg

# Test connection from EC2
psql -h <rds-endpoint> -U recruitment_admin -d recruitment
```

### Chroma not responding
```bash
# Check Chroma container on its EC2 instance
docker logs chroma

# Verify security group allows port 8000
aws ec2 describe-security-groups --group-names recruitment-chroma-sg
```

## Costs

Estimated monthly costs (us-east-1):
- **EC2 (2x t3.small)**: ~$30-40
- **RDS (db.t3.micro)**: ~$30-40
- **Chroma EC2 (t3.small)**: ~$15-20
- **Data Transfer**: ~$0-10
- **Load Balancer**: ~$16 (fixed)

**Total: ~$90-130/month**

## SSL/HTTPS Setup (Optional)

To enable HTTPS, you'll need an SSL certificate:

1. Request certificate from ACM:
```bash
aws acm request-certificate \
  --domain-name career.pom100.com \
  --validation-method DNS
```

2. Update `terraform/ec2.tf` to uncomment the HTTPS listener section

3. Redeploy:
```bash
terraform apply
```

## Cleanup

To destroy all AWS resources:

```bash
cd terraform
terraform destroy

# Confirm by typing 'yes' when prompted
```

**Warning**: This will permanently delete all resources including the database. Ensure you have backups if needed.

## Environment Variables

Application environment variables are set in the EC2 user data script. To update:

1. Modify `terraform/user_data.sh`
2. Run `terraform apply` (EC2 instances will be replaced)

For quick updates without instance replacement:
```bash
# SSH into instance
# Edit .env file
nano /home/ec2-user/agentics/.env

# Restart services
docker-compose restart
```

## Next Steps

1. Configure Route53 with your domain registrar
2. Set up SSL/HTTPS with ACM
3. Configure CloudWatch monitoring and alarms
4. Set up backup policies for RDS
5. Configure auto-scaling policies based on CPU/memory
6. Set up CI/CD pipeline for automated deployments

## Support

For issues, check:
- AWS CloudWatch Logs
- Terraform state file: `terraform/terraform.tfstate`
- EC2 console for instance details
- Application logs via Docker Compose

## Security Notes

⚠️ **Important for Production**:
- [ ] Change database password (currently generated, exposed in Terraform state)
- [ ] Use private subnets for RDS
- [ ] Restrict security group ingress to known IPs
- [ ] Enable encryption at rest for RDS
- [ ] Use AWS Secrets Manager for sensitive data
- [ ] Enable VPC Flow Logs for monitoring
- [ ] Set up WAF (Web Application Firewall) on ALB
- [ ] Enable RDS backups and enable deletion protection
- [ ] Use S3 for Terraform state with encryption and versioning

