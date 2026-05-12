resource "aws_cognito_user_pool" "app" {
  count = var.enable_cognito ? 1 : 0

  name                     = "${local.name}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = upper(var.cognito_mfa_configuration)

  admin_create_user_config {
    allow_admin_create_user_only = !var.cognito_self_signup_enabled
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 5
      max_length = 255
    }
  }

  dynamic "software_token_mfa_configuration" {
    for_each = upper(var.cognito_mfa_configuration) == "OFF" ? [] : [1]

    content {
      enabled = true
    }
  }
}

resource "aws_cognito_user_pool_domain" "app" {
  count = var.enable_cognito ? 1 : 0

  domain       = local.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.app[0].id
}

resource "aws_cognito_user_pool_client" "frontend" {
  count = var.enable_cognito ? 1 : 0

  name         = "${local.name}-frontend"
  user_pool_id = aws_cognito_user_pool.app[0].id

  generate_secret                      = var.cognito_generate_client_secret
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = local.cognito_oauth_scopes
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = local.cognito_callback_urls
  logout_urls                          = local.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 15
  id_token_validity      = 15
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  lifecycle {
    precondition {
      condition     = length(local.cognito_callback_urls) > 0
      error_message = "Cognito requires at least one callback URL. Set frontend_base_url or cognito_callback_urls."
    }

    precondition {
      condition     = !var.cognito_auto_provision_users || length(var.cognito_allowed_signup_email_domains) > 0
      error_message = "Set cognito_allowed_signup_email_domains when cognito_auto_provision_users is enabled."
    }
  }
}

resource "aws_cognito_user_group" "rbac_roles" {
  for_each = var.enable_cognito ? toset(["SUPER_ADMIN", "HR_MANAGER", "DEPT_HEAD", "EMPLOYEE", "AUDITOR"]) : toset([])

  user_pool_id = aws_cognito_user_pool.app[0].id
  name         = each.value
  description  = "Maps Cognito group ${each.value} to WorkforceIQ RBAC."
}
