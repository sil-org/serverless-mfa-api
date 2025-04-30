variable "aws_region" {
  default = "us-east-1"
}

variable "aws_region_secondary" {
  default = "us-west-2"
}

variable "aws_access_key_id" {
  default = null
}

variable "aws_secret_access_key" {
  default = null
}

variable "cloudflare_token" {
  description = "The Cloudflare limited access API token"
  type        = string
}

variable "cloudflare_domain" {
  description = "Cloudflare zone (domain) for DNS records"
  type        = string
}

/*
 * AWS tag values
 */

variable "app_customer" {
  description = "customer name to use for the itse_app_customer tag"
  type        = string
  default     = "shared"
}

variable "app_environment" {
  description = "environment name to use for the itse_app_environment tag, e.g. staging, production"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "WARNING: Changing this will replace (delete) resources, even your database. Used in naming and tagging resources."
  type        = string
  default     = "mfa-api"
}


/*
  Variables for Backblaze B2 configuration
 */

variable "b2_endpoint_url" {
  description = "Backblaze B2 S3-compatible endpoint URL"
  type        = string
  default     = "https://s3.us-west-004.backblazeb2.com" # Default to a common region
}

variable "b2_application_key_id" {
  description = "Backblaze B2 Application Key ID"
  type        = string
  sensitive   = true
}

variable "b2_application_key" {
  description = "Backblaze B2 Application Key"
  type        = string
  sensitive   = true
}

variable "b2_bucket_name" {
  description = "Backblaze B2 Bucket Name"
  type        = string
}
