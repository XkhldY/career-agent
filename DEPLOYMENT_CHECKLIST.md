# AWS Deployment Checklist

Complete this checklist before and after deployment to career.pom100.com

## ✅ Pre-Deployment

### Prerequisites
- [ ] AWS account access with appropriate permissions
- [ ] AWS CLI installed: `aws --version`
- [ ] Terraform installed: `terraform --version`
- [ ] Git installed: `git --version`
- [ ] GitHub access for repository cloning

### AWS Configuration
- [ ] AWS credentials configured: `aws sts get-caller-identity`
- [ ] Route53 hosted zone created for pom100.com
- [ ] IAM user has EC2, RDS, ALB, Route53 permissions
- [ ] AWS region selected (us-east-1 recommended)

### Application Preparation
- [ ] GitHub repository is public or has access token
- [ ] Repository branch is clean and deployable
- [ ] All secrets in .env are non-sensitive or placeholders
- [ ] Docker Compose works locally: `docker-compose up`
- [ ] No uncommitted changes in repository

## 🚀 Deployment Phase

### Infrastructure Deployment
- [ ] Run: `chmod +x scripts/deploy.sh`
- [ ] Run: `scripts/deploy.sh`
- [ ] Confirm deployment with "yes"
- [ ] Wait for Terraform apply to complete (10-15 minutes)
- [ ] Review outputs (ALB DNS, RDS endpoint, Chroma URL)
- [ ] Save outputs: `cd terraform && terraform output -json > outputs.json`

### Initial Verification
- [ ] All AWS resources created successfully
- [ ] EC2 instances launching in Auto Scaling Group
- [ ] RDS database accessible
- [ ] Load Balancer active
- [ ] Security groups configured correctly

### Application Startup
- [ ] Wait 5-10 minutes for EC2 instances to initialize
- [ ] Docker containers pulling images
- [ ] Backend application starting on port 8000
- [ ] Frontend application starting on port 3000
- [ ] Chroma vector DB running on port 8000

## 🔍 Post-Deployment Verification

### Infrastructure Tests
- [ ] Run: `chmod +x scripts/verify-deployment.sh`
- [ ] Run: `scripts/verify-deployment.sh`
- [ ] PostgreSQL connectivity test passed
- [ ] Chroma API responding
- [ ] ALB responding with 200/301 status

### Application Access
- [ ] Access via ALB DNS:
  - [ ] Frontend: `http://<ALB-DNS>:3000`
  - [ ] Backend: `http://<ALB-DNS>:8000`
  - [ ] API Health: `http://<ALB-DNS>:8000/health`
- [ ] Frontend loads without errors
- [ ] API endpoints responding
- [ ] Database queries working

### EC2 Instance Checks
- [ ] SSH into instance: `aws ec2-instance-connect open-tunnel`
- [ ] Docker running: `docker ps`
- [ ] All containers healthy:
  - [ ] PostgreSQL container running
  - [ ] Chroma container running
  - [ ] Backend container running
  - [ ] Frontend container running
- [ ] Logs show no critical errors: `docker-compose logs`

### Database Verification
- [ ] Connect to PostgreSQL: `psql -h <RDS_ENDPOINT>`
- [ ] Database exists: `\l`
- [ ] Tables created: `\dt`
- [ ] Data accessible and queryable
- [ ] Backups enabled and running

### Vector Database (Chroma)
- [ ] Chroma API accessible: `curl http://<CHROMA_HOST>:8000/api/v1/collections`
- [ ] Collections can be created
- [ ] Embeddings can be added
- [ ] Queries working correctly

## 🌐 DNS Configuration

### Route53 Setup
- [ ] Hosted zone for pom100.com exists
- [ ] Create CNAME record:
  - [ ] Name: `career.pom100.com`
  - [ ] Type: CNAME
  - [ ] Value: `<ALB-DNS-NAME>`
  - [ ] TTL: 300
- [ ] DNS record propagated (5-15 minutes)
- [ ] Test DNS: `nslookup career.pom100.com`
- [ ] Access via domain: `http://career.pom100.com:3000`

## 🔐 Security Hardening

### Network Security
- [ ] Security groups restrict unnecessary ports
- [ ] RDS security group only allows port 5432
- [ ] ALB security group allows 80/443 only
- [ ] EC2 security group allows SSH only from trusted IPs
- [ ] All security groups have descriptive names

### Data Security
- [ ] RDS storage encrypted
- [ ] Database backups enabled (7 days retention)
- [ ] Backup encryption enabled
- [ ] No hardcoded secrets in .env or config
- [ ] Secrets stored in AWS Secrets Manager

### Access Control
- [ ] IAM roles minimal and specific
- [ ] No root credentials used
- [ ] EC2 instances have limited IAM permissions
- [ ] CloudWatch logs retention set appropriately
- [ ] VPC Flow Logs enabled (optional)

## 📊 Monitoring Setup

### CloudWatch Configuration
- [ ] CloudWatch agent installed on EC2
- [ ] Application logs sent to CloudWatch
- [ ] Database performance insights enabled
- [ ] ALB access logs enabled
- [ ] CPU and memory metrics visible

### Alarms Created
- [ ] High CPU alarm (> 80%)
- [ ] High memory alarm (> 80%)
- [ ] RDS storage alarm (> 80%)
- [ ] ALB unhealthy target alarm
- [ ] Database connection pool alarm

### Logging
- [ ] Application logs available in CloudWatch
- [ ] Error logs properly categorized
- [ ] Request logs being collected
- [ ] Log retention set to 7-30 days

## 🔄 Auto-Scaling Verification

### Scaling Group Status
- [ ] ASG created with correct min/max/desired
- [ ] Current instances: Check in AWS console
- [ ] Scaling policies attached
- [ ] Health checks configured (30 second interval)
- [ ] Target group health checks passing

### Scale Testing (Optional)
- [ ] Trigger high load (simulate traffic)
- [ ] Verify instances scale up
- [ ] Verify instances scale down after load drops
- [ ] No service interruption during scaling

## 📈 Performance Baseline

### Response Times
- [ ] Frontend load time: < 3 seconds
- [ ] API response time: < 500ms
- [ ] Database query time: < 200ms
- [ ] Vector DB query time: < 1 second

### Resource Usage
- [ ] EC2 CPU: Normal 10-30%
- [ ] EC2 Memory: Normal 20-40%
- [ ] RDS CPU: Normal 5-15%
- [ ] RDS Memory: Normal usage expected
- [ ] Network bandwidth: Check ALB metrics

## 🎯 Application Functionality

### Backend API
- [ ] Health endpoint working: `/health`
- [ ] CORS configured correctly
- [ ] Authentication working if enabled
- [ ] Database operations working
- [ ] Vector DB operations working
- [ ] All endpoints accessible

### Frontend Application
- [ ] Pages loading correctly
- [ ] Navigation working
- [ ] Forms submitting
- [ ] API calls completing
- [ ] No console errors
- [ ] No network errors

## 🧹 Cleanup & Maintenance

### Repository
- [ ] Git repository clean: `git status`
- [ ] All changes committed
- [ ] Remote added: `git remote -v`
- [ ] Pushed to GitHub: `git push`
- [ ] Deployment branch protected

### Documentation
- [ ] Deployment guide reviewed
- [ ] Team members have access
- [ ] Runbooks created for common issues
- [ ] Emergency procedures documented
- [ ] Contact information shared

### Cost Management
- [ ] Billing alerts configured (set to $150)
- [ ] Unused resources identified
- [ ] Auto-scaling limits appropriate
- [ ] Reserved instances considered
- [ ] Cost analysis available

## 🔄 Post-Deployment (Day 1)

- [ ] Monitor application for 24 hours
- [ ] Check CloudWatch metrics and alarms
- [ ] Review logs for errors
- [ ] Verify backups are running
- [ ] Test failover procedures
- [ ] Document any issues
- [ ] Adjust auto-scaling if needed

## 📞 Support & Troubleshooting

### If Issues Arise
- [ ] Check CloudWatch logs first
- [ ] SSH to instance: `aws ec2-instance-connect open-tunnel`
- [ ] Review Docker logs: `docker-compose logs -f`
- [ ] Check Terraform state: `terraform show`
- [ ] Review security groups
- [ ] Check RDS event logs

### Documentation References
- [ ] AWS_DEPLOYMENT_SETUP.md - Setup overview
- [ ] DEPLOYMENT_GUIDE.md - Detailed guide
- [ ] QUICK_START_DEPLOYMENT.md - Fast track
- [ ] README.md - Application info
- [ ] terraform/*.tf - Infrastructure code

## ✨ Success Criteria

Your deployment is successful when:

- ✅ All infrastructure created without errors
- ✅ Application accessible via ALB and DNS
- ✅ Database connected and working
- ✅ Vector DB (Chroma) functional
- ✅ Auto-scaling responding to load
- ✅ Monitoring and alarms active
- ✅ No critical errors in logs
- ✅ Performance metrics acceptable
- ✅ Security groups properly configured
- ✅ Backups scheduled and working

---

**Date Deployed**: ________________  
**Deployed By**: ________________  
**Environment**: Production  
**Domain**: career.pom100.com  
**ALB DNS**: ________________  

**Sign-off**: ________________

