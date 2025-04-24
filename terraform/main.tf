
locals {
  /* The app_env is used in some resource names. */
  app_env = var.app_environment == "production" ? "prod" : "dev"
}

/*
 * Create IAM user for Serverless framework to use to deploy the lambda function
 */
module "serverless_user" {
  count   = var.app_environment == "staging" ? 1 : 0
  source  = "silinternational/serverless-user/aws"
  version = "~> 0.4.2"

  app_name           = var.app_name
  aws_region_policy  = "*"
  enable_api_gateway = true

  extra_policies = [
    jsonencode(
      {
        "Version" : "2012-10-17",
        "Statement" : [
          {
            "Effect" : "Allow",
            "Action" : [
              "dynamodb:DescribeGlobalTableSettings",
              "dynamodb:DescribeGlobalTable"
            ],
            "Resource" : "arn:aws:dynamodb:*:*:global-table/${var.app_name}_*"
          },
          {
            "Effect" : "Allow",
            "Action" : [
              "dynamodb:BatchWriteItem",
              "dynamodb:CreateTable",
              "dynamodb:CreateTableReplica",
              "dynamodb:DeleteItem",
              "dynamodb:DescribeContinuousBackups",
              "dynamodb:DescribeContributorInsights",
              "dynamodb:DescribeKinesisStreamingDestination",
              "dynamodb:DescribeTable",
              "dynamodb:DescribeTimeToLive",
              "dynamodb:GetItem",
              "dynamodb:ListTagsOfResource",
              "dynamodb:PutItem",
              "dynamodb:Query",
              "dynamodb:Scan",
              "dynamodb:TagResource",
              "dynamodb:UntagResource",
              "dynamodb:UpdateItem",
              "dynamodb:UpdateTable"
            ],
            "Resource" : "arn:aws:dynamodb:*:*:table/${var.app_name}_*"
          },
          {
            "Effect" : "Allow",
            "Action" : [
              "dynamodb:Scan",
              "dynamodb:Query"
            ],
            "Resource" : "arn:aws:dynamodb:*:*:table/${var.app_name}_*/index/*"
          },
          {
            "Effect" : "Allow",
            "Action" : [
              "iam:CreateServiceLinkedRole",
              "iam:TagRole",
              "iam:UntagRole"
            ],
            "Resource" : "arn:aws:iam::*:role/*"
          },
          {
            "Effect" : "Allow",
            "Action" : [
              "ssm:GetParameter",
              "ssm:GetParameters"
            ],
            "Resource" : [
              "arn:aws:ssm:*:*:parameter/${var.app_name}/${local.app_env}/b2_*"
            ]
          },
          {
            "Effect" : "Allow",
            "Action" : [
              "lambda:GetFunction",
              "lambda:CreateFunction",
              "lambda:UpdateFunctionCode",
              "lambda:UpdateFunctionConfiguration",
              "lambda:ListVersionsByFunction",
              "lambda:PublishVersion",
              "lambda:CreateAlias",
              "lambda:UpdateAlias",
              "lambda:DeleteAlias",
              "events:PutRule",
              "events:PutTargets",
              "events:RemoveTargets",
              "events:DeleteRule"
            ],
            "Resource" : "*"
          }
        ]
      }
    )
  ]
}

/*
 * Manage custom domain name resources (used primarily to ease failovers).
 */
module "dns_for_failover" {
  source  = "silinternational/serverless-api-dns-for-failover/aws"
  version = "~> 0.6.0"

  api_name             = "${local.app_env}-${var.app_name}"
  cloudflare_zone_name = var.cloudflare_domain
  serverless_stage     = local.app_env
  subdomain            = var.app_name

  providers = {
    aws           = aws
    aws.secondary = aws.secondary
  }
}

/*
 * Manage DynamoDB tables used by the functions.
 */
resource "aws_dynamodb_table" "api_keys" {
  name                        = "${var.app_name}_${local.app_env}_api-key_global"
  hash_key                    = "value"
  billing_mode                = "PAY_PER_REQUEST"
  deletion_protection_enabled = true
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "value"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  replica {
    region_name = var.aws_region_secondary
  }

  lifecycle {
    ignore_changes = [replica]
  }
}

resource "aws_dynamodb_table" "totp" {
  name                        = "${var.app_name}_${local.app_env}_totp_global"
  hash_key                    = "uuid"
  billing_mode                = "PAY_PER_REQUEST"
  deletion_protection_enabled = true
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "uuid"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  replica {
    region_name = var.aws_region_secondary
  }

  lifecycle {
    ignore_changes = [replica]
  }
}

resource "aws_dynamodb_table" "u2f" {
  name                        = "${var.app_name}_${local.app_env}_u2f_global"
  hash_key                    = "uuid"
  billing_mode                = "PAY_PER_REQUEST"
  deletion_protection_enabled = true
  stream_enabled              = true
  stream_view_type            = "NEW_IMAGE"

  attribute {
    name = "uuid"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  replica {
    region_name = var.aws_region_secondary
  }

  lifecycle {
    ignore_changes = [replica]
  }
}

resource "aws_ssm_parameter" "b2_endpoint_url" {
  name  = "/${var.app_name}/${local.app_env}/b2_endpoint_url"
  type  = "String"
  value = var.b2_endpoint_url
}

resource "aws_ssm_parameter" "b2_application_key_id" {
  name  = "/${var.app_name}/${local.app_env}/b2_application_key_id"
  type  = "SecureString"
  value = var.b2_application_key_id
}

resource "aws_ssm_parameter" "b2_application_key" {
  name  = "/${var.app_name}/${local.app_env}/b2_application_key"
  type  = "SecureString"
  value = var.b2_application_key
}

resource "aws_ssm_parameter" "b2_bucket_name" {
  name  = "/${var.app_name}/${local.app_env}/b2_bucket_name"
  type  = "String"
  value = var.b2_bucket_name
}
