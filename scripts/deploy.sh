#!/bin/bash
# Deployment script for AWS infrastructure

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

echo "🚀 Starting AWS deployment..."
echo "Project root: $PROJECT_ROOT"
echo "Terraform directory: $TERRAFORM_DIR"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured properly."
    exit 1
fi

# Initialize Terraform
cd "$TERRAFORM_DIR"
echo "Initializing Terraform..."
terraform init

# Validate Terraform
echo "Validating Terraform configuration..."
terraform validate

# Plan the deployment
echo "Planning Terraform deployment..."
terraform plan -out=tfplan

# Apply the deployment
echo "Applying Terraform configuration..."
read -p "Do you want to proceed with deployment? (yes/no) " -n 3 -r
echo
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    terraform apply tfplan

    # Get outputs
    echo ""
    echo "✅ Deployment completed!"
    echo ""
    echo "=== Deployment Outputs ==="
    terraform output

    # Save outputs to a file
    terraform output -json > ../deployment-outputs.json
    echo "Outputs saved to deployment-outputs.json"
else
    echo "Deployment cancelled."
    exit 1
fi
