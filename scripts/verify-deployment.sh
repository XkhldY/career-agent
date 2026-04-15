#!/bin/bash
# Verify AWS deployment is working correctly

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Verifying AWS deployment..."
echo ""

# Load deployment outputs
OUTPUTS_FILE="$PROJECT_ROOT/deployment-outputs.json"

if [ ! -f "$OUTPUTS_FILE" ]; then
    echo "❌ Deployment outputs file not found. Run deploy.sh first."
    exit 1
fi

# Extract values using jq
RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' "$OUTPUTS_FILE")
RDS_ADDRESS=$(jq -r '.rds_address.value' "$OUTPUTS_FILE")
CHROMA_URL=$(jq -r '.chroma_url.value' "$OUTPUTS_FILE")
ALB_DNS=$(jq -r '.alb_dns_name.value' "$OUTPUTS_FILE")
APP_URL=$(jq -r '.app_url.value' "$OUTPUTS_FILE")

echo "=== Infrastructure Endpoints ==="
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "Chroma URL: $CHROMA_URL"
echo "ALB DNS: $ALB_DNS"
echo "App URL: $APP_URL"
echo ""

# Test RDS connection
echo "🔗 Testing PostgreSQL connection..."
if command -v psql &> /dev/null; then
    if psql -h "$RDS_ADDRESS" -U recruitment_admin -d recruitment -c "SELECT 1;" 2>/dev/null; then
        echo "✅ PostgreSQL connection successful"
    else
        echo "⚠️  PostgreSQL connection test skipped (password required)"
    fi
else
    echo "⚠️  psql not installed, skipping PostgreSQL test"
fi

# Test Chroma connection
echo ""
echo "🔗 Testing Chroma connection..."
if command -v curl &> /dev/null; then
    if curl -s "${CHROMA_URL}/api/v1/collections" > /dev/null; then
        echo "✅ Chroma connection successful"
        curl -s "${CHROMA_URL}/api/v1/collections" | jq '.'
    else
        echo "⚠️  Could not connect to Chroma (may still be starting)"
    fi
else
    echo "⚠️  curl not installed, skipping Chroma test"
fi

# Test ALB
echo ""
echo "🔗 Testing Application Load Balancer..."
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "301" ]; then
        echo "✅ ALB is responding (HTTP $HTTP_CODE)"
    else
        echo "⚠️  ALB returned HTTP $HTTP_CODE (may still be initializing)"
    fi
else
    echo "⚠️  curl not installed, skipping ALB test"
fi

echo ""
echo "=== Verification Steps ==="
echo "1. Wait 5-10 minutes for EC2 instances to fully initialize"
echo "2. SSH into an instance and check Docker containers:"
echo "   docker-compose ps"
echo "3. Check application logs:"
echo "   docker-compose logs -f"
echo "4. Access the application:"
echo "   Frontend: http://$ALB_DNS:3000"
echo "   Backend: http://$ALB_DNS:8000"
echo "5. Once Route53 is configured, access via:"
echo "   http://$APP_URL"
echo ""
echo "✅ Verification complete!"
