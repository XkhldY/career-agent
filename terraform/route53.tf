# ---------------------------------------------------------------------------
# Route53 DNS Configuration
# ---------------------------------------------------------------------------

# Get the hosted zone for pom100.com
# Note: You must create this hosted zone manually or have it already exist
data "aws_route53_zone" "main" {
  name = var.domain_name
}

# DNS record for the application
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.app_domain
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# Output the DNS record
output "app_dns_record" {
  description = "DNS record for the application"
  value       = aws_route53_record.app.fqdn
}
