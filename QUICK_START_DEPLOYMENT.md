# Quick Start: Deploy to AWS

This document provides a streamlined path to deploy the Agentics application to AWS.

## ✅ Pre-Deployment Checklist

- [ ] AWS account with administrator access
- [ ] AWS CLI configured (`aws configure`)
- [ ] Terraform installed (`terraform --version`)
- [ ] Domain `pom100.com` configured in Route53
- [ ] GitHub repository is public or you have a personal access token

## 🚀 Deployment in 5 Minutes

### 1. **Verify Prerequisites**
```bash
cd /Users/khaled/agentics

# Check AWS access
aws sts get-caller-identity

# Check Terraform
terraform -v

# Check git repo
git status
```

### 2. **Deploy Infrastructure**
```bash
# Make script executable
chmod +x scripts/deploy.sh

# Run deployment
scripts/deploy.sh

# When prompted, type 'yes' to confirm
```

### 3. **Wait for Initialization** ⏳
EC2 instances need 5-10 minutes to:
- Boot
- Install Docker
- Pull code from GitHub
- Build and start containers

Monitor progress:
```bash
# Check instance status
aws ec2 describe-instance-status \
  --filters "Name=instance-state-name,Values=running" \
  --query 'InstanceStatuses[].InstanceStatus.Status'

# SSH into instance when ready
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names recruitment-asg \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

aws ec2-instance-connect open-tunnel --instance-id $INSTANCE_ID
```

### 4. **Verify Deployment**
```bash
chmod +x scripts/verify-deployment.sh
scripts/verify-deployment.sh
```

### 5. **Access Application**

**Get ALB DNS:**
```bash
cd terraform
terraform output alb_dns_name
```

Then access:
- **Backend API**: http://<ALB-DNS>:8000
- **Frontend**: http://<ALB-DNS>:3000

**Example output:**
```
Frontend: http://recruitment-alb-123456789.us-east-1.elb.amazonaws.com:3000
Backend: http://recruitment-alb-123456789.us-east-1.elb.amazonaws.com:8000
```

### 6. **Configure DNS (Optional)**

Once verified, configure career.pom100.com:

```bash
# Get ALB details
cd terraform
terraform output alb_dns_name

# Create Route53 record (via AWS Console or CLI)
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "career.pom100.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<ALB-DNS>"}]
      }
    }]
  }'
```

Then access:
- Frontend: http://career.pom100.com:3000
- Backend: http://career.pom100.com:8000

## 📊 What Gets Created

| Resource | Type | Size | Cost/Month |
|----------|------|------|-----------|
| EC2 Instances | t3.small | 2-4 | $30-40 |
| RDS PostgreSQL | db.t3.micro | 20GB | $30-40 |
| Chroma Server | t3.small | 1 | $15-20 |
| Load Balancer | ALB | - | $16 |
| **Total** | - | - | **~$100** |

## 🔍 Monitoring

### View Logs
```bash
# Get an instance ID
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names recruitment-asg \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

# Connect to instance
aws ec2-instance-connect open-tunnel --instance-id $INSTANCE_ID

# Then SSH and check logs
docker-compose logs -f
```

### View Deployment Outputs
```bash
cd terraform

# Show all outputs
terraform output

# Show specific output
terraform output alb_dns_name
terraform output rds_endpoint
terraform output chroma_url
```

## 🛑 Troubleshooting

### "Deployment failed"
```bash
# Check Terraform state
cd terraform
terraform show

# Validate configuration
terraform validate

# Check for errors
terraform plan
```

### "Cannot connect to database"
```bash
# Verify security groups
aws ec2 describe-security-groups --group-names recruitment-rds-sg

# Test from EC2
psql -h <RDS_ENDPOINT> -U recruitment_admin -d recruitment
```

### "Chroma not responding"
```bash
# Check Chroma instance
aws ec2 describe-instances --filters "Name=tag:Name,Values=recruitment-chroma"

# SSH and check logs
docker logs chroma
```

### "Application loading slowly"
- EC2 instances still initializing (wait 10+ minutes)
- Check instance logs: `docker-compose logs`
- Verify CPU/memory: `docker stats`

## 🧹 Cleanup

To destroy all resources and **stop incurring costs**:

```bash
cd terraform
terraform destroy

# Confirm when prompted
```

This deletes:
- All EC2 instances
- RDS database
- Load Balancer
- Security groups
- Everything except Route53 hosted zone

## 📝 Environment Variables

To update application configuration:

1. Edit `terraform/user_data.sh`
2. Change the `.env` section
3. Run `terraform apply`

Or, SSH into an instance and edit directly:
```bash
ssh ec2-user@<INSTANCE_IP>
nano /home/ec2-user/agentics/.env
docker-compose restart
```

## 🔒 Production Considerations

Before going live, implement:

- [ ] **SSL/HTTPS**: Use ACM certificate + ALB HTTPS listener
- [ ] **Database**: Private subnet, enhanced backups, encryption
- [ ] **Security**: WAF, VPC security groups, Secrets Manager
- [ ] **Monitoring**: CloudWatch alarms, log aggregation
- [ ] **Auto-scaling**: CPU-based scaling policies
- [ ] **CI/CD**: GitHub Actions for automated deployments

See `DEPLOYMENT_GUIDE.md` for detailed production setup.

## 📞 Support

For issues:
1. Check CloudWatch logs: `aws logs tail /aws/ec2/recruitment --follow`
2. SSH into instance and check `docker-compose logs`
3. Review Terraform outputs: `terraform output -json > debug.json`
4. Check AWS Console for resource status

## 🎯 Next Steps

After successful deployment:

1. ✅ Test application functionality
2. ✅ Configure DNS records
3. ✅ Set up SSL/HTTPS
4. ✅ Configure monitoring and alerts
5. ✅ Set up backup policies
6. ✅ Plan capacity and auto-scaling

Happy deploying! 🚀
