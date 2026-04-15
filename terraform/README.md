# Terraform – AWS (RDS + Chroma EC2)

## Resources

- **RDS PostgreSQL 16** – DB for jobs and job_runs
- **EC2 (Chroma)** – Single instance running Chroma in Docker on port 8000

## Apply

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Get outputs for .env

After apply:

```bash
terraform output -raw database_url   # -> DATABASE_URL (add ?sslmode=require if not present)
terraform output -raw chroma_host    # -> CHROMA_HOST
```

Example `.env`:

```
DATABASE_URL=postgresql://recruitment_admin:xxx@recruitment-db.xxx.rds.amazonaws.com:5432/recruitment?sslmode=require
CHROMA_HOST=1.2.3.4
CHROMA_PORT=8000
```

## Destroy

```bash
terraform destroy
```
