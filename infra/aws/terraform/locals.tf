locals {
  name         = "${var.project_name}-${var.environment}"
  ecr_registry = split("/", aws_ecr_repository.app.repository_url)[0]
  image_uri    = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  public_scheme   = var.acm_certificate_arn == "" ? "http" : "https"
  public_host     = var.app_domain == "" ? aws_lb.app.dns_name : var.app_domain
  public_base_url = "${local.public_scheme}://${local.public_host}"

  effective_cors_origins = length(var.frontend_origins) > 0 ? join(",", var.frontend_origins) : var.cors_origins
  effective_frontend_origin = var.frontend_base_url != "" ? trimsuffix(var.frontend_base_url, "/") : (
    length(var.frontend_origins) > 0 ? trimsuffix(var.frontend_origins[0], "/") : ""
  )

  cognito_domain_prefix = var.cognito_domain_prefix != "" ? var.cognito_domain_prefix : substr(
    lower("${var.project_name}-${var.environment}-${random_id.suffix.hex}"),
    0,
    63,
  )
  cognito_callback_urls = length(var.cognito_callback_urls) > 0 ? var.cognito_callback_urls : (
    local.effective_frontend_origin == "" ? [] : ["${local.effective_frontend_origin}/auth/callback"]
  )
  cognito_logout_urls = length(var.cognito_logout_urls) > 0 ? var.cognito_logout_urls : (
    local.effective_frontend_origin == "" ? [] : [local.effective_frontend_origin]
  )
  cognito_oauth_scopes       = ["openid", "email", "profile"]
  cognito_issuer             = var.enable_cognito ? "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.app[0].id}" : ""
  cognito_jwks_uri           = var.enable_cognito ? "${local.cognito_issuer}/.well-known/jwks.json" : ""
  cognito_hosted_ui_base_url = var.enable_cognito ? "https://${aws_cognito_user_pool_domain.app[0].domain}.auth.${var.aws_region}.amazoncognito.com" : ""
  cognito_login_url          = var.enable_cognito && length(local.cognito_callback_urls) > 0 ? "${local.cognito_hosted_ui_base_url}/login?client_id=${aws_cognito_user_pool_client.frontend[0].id}&response_type=code&scope=${urlencode(join(" ", local.cognito_oauth_scopes))}&redirect_uri=${urlencode(local.cognito_callback_urls[0])}" : ""
  cognito_logout_url         = var.enable_cognito && length(local.cognito_logout_urls) > 0 ? "${local.cognito_hosted_ui_base_url}/logout?client_id=${aws_cognito_user_pool_client.frontend[0].id}&logout_uri=${urlencode(local.cognito_logout_urls[0])}" : ""

  database_url = "mysql+pymysql://workforceiq:${random_password.db_password.result}@${aws_db_instance.mysql.address}:3306/workforceiq?ssl_ca=/opt/workforceiq/global-bundle.pem"
  redis_url    = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"

  app_env = {
    WORKFORCEIQ_CONFIG                        = "production"
    FLASK_APP                                 = "run.py"
    APP_VERSION                               = "3.0.0"
    COMPANY_NAME                              = "WorkforceIQ"
    DEFAULT_ORGANIZATION_ID                   = "org-demo"
    SECRET_KEY                                = random_password.app_secret.result
    JWT_SECRET_KEY                            = random_password.jwt_secret.result
    JWT_ACCESS_TOKEN_EXPIRES                  = "900"
    JWT_REFRESH_TOKEN_EXPIRES                 = "2592000"
    DATABASE_URL                              = local.database_url
    REDIS_URL                                 = local.redis_url
    CELERY_BROKER_URL                         = local.redis_url
    CELERY_RESULT_BACKEND                     = local.redis_url
    ENABLE_DEV_AUTH                           = "false"
    RATE_LIMIT_BACKEND                        = "redis"
    RATE_LIMIT_PER_MINUTE                     = "100"
    AUTH_LOCKOUT_THRESHOLD                    = "5"
    AUTH_LOCKOUT_MINUTES                      = "15"
    OIDC_ENABLED                              = var.enable_cognito ? "true" : "false"
    OIDC_ISSUER                               = local.cognito_issuer
    OIDC_AUDIENCE                             = var.enable_cognito ? aws_cognito_user_pool_client.frontend[0].id : ""
    OIDC_JWKS_URI                             = local.cognito_jwks_uri
    OIDC_JWKS_JSON                            = ""
    OIDC_CLOCK_SKEW_SECONDS                   = "60"
    OIDC_REQUIRE_VERIFIED_EMAIL               = "true"
    OIDC_AUTO_PROVISION_USERS                 = var.enable_cognito && var.cognito_auto_provision_users ? "true" : "false"
    OIDC_AUTO_PROVISION_DEFAULT_ROLE          = upper(var.cognito_auto_provision_default_role)
    OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS = join(",", var.cognito_allowed_signup_email_domains)
    MAX_EXPORT_ROWS                           = "500"
    ML_STALE_DAYS                             = "30"
    CORS_ORIGINS                              = local.effective_cors_origins
    LOG_LEVEL                                 = "INFO"
    STRUCTURED_LOGS                           = "true"
    BACKUP_DIRECTORY                          = "backups"
    BACKUP_BUCKET                             = aws_s3_bucket.backups.bucket
    AWS_REGION                                = var.aws_region
    WORKFORCEIQ_IMAGE                         = local.image_uri
    MYSQL_HOST                                = aws_db_instance.mysql.address
    MYSQL_DATABASE                            = "workforceiq"
    MYSQL_USER                                = "workforceiq"
    MYSQL_PASSWORD                            = random_password.db_password.result
    REDIS_HOST                                = aws_elasticache_replication_group.redis.primary_endpoint_address
    PUBLIC_BASE_URL                           = local.public_base_url
  }
}
