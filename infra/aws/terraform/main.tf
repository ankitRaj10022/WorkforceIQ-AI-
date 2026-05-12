data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

locals {
  name         = "${var.project_name}-${var.environment}"
  ecr_registry = split("/", aws_ecr_repository.app.repository_url)[0]
  image_uri    = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  public_scheme   = var.acm_certificate_arn == "" ? "http" : "https"
  public_host     = var.app_domain == "" ? aws_lb.app.dns_name : var.app_domain
  public_base_url = "${local.public_scheme}://${local.public_host}"

  database_url = "mysql+pymysql://workforceiq:${random_password.db_password.result}@${aws_db_instance.mysql.address}:3306/workforceiq?ssl_ca=/opt/workforceiq/global-bundle.pem"
  redis_url    = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"

  app_env = {
    WORKFORCEIQ_CONFIG      = "production"
    FLASK_APP               = "run.py"
    APP_VERSION             = "3.0.0"
    COMPANY_NAME            = "WorkforceIQ"
    DEFAULT_ORGANIZATION_ID = "org-demo"
    SECRET_KEY              = random_password.app_secret.result
    JWT_SECRET_KEY          = random_password.jwt_secret.result
    JWT_ACCESS_TOKEN_EXPIRES = "900"
    JWT_REFRESH_TOKEN_EXPIRES = "2592000"
    DATABASE_URL            = local.database_url
    REDIS_URL               = local.redis_url
    CELERY_BROKER_URL       = local.redis_url
    CELERY_RESULT_BACKEND   = local.redis_url
    ENABLE_DEV_AUTH         = "false"
    RATE_LIMIT_BACKEND      = "redis"
    RATE_LIMIT_PER_MINUTE   = "100"
    AUTH_LOCKOUT_THRESHOLD  = "5"
    AUTH_LOCKOUT_MINUTES    = "15"
    OIDC_ENABLED            = "false"
    OIDC_ISSUER             = ""
    OIDC_AUDIENCE           = ""
    OIDC_JWKS_URI           = ""
    OIDC_JWKS_JSON          = ""
    OIDC_CLOCK_SKEW_SECONDS = "60"
    OIDC_REQUIRE_VERIFIED_EMAIL = "true"
    MAX_EXPORT_ROWS         = "500"
    ML_STALE_DAYS           = "30"
    CORS_ORIGINS            = var.cors_origins
    LOG_LEVEL               = "INFO"
    STRUCTURED_LOGS         = "true"
    BACKUP_DIRECTORY        = "backups"
    BACKUP_BUCKET           = aws_s3_bucket.backups.bucket
    AWS_REGION              = var.aws_region
    WORKFORCEIQ_IMAGE       = local.image_uri
    MYSQL_HOST              = aws_db_instance.mysql.address
    MYSQL_DATABASE          = "workforceiq"
    MYSQL_USER              = "workforceiq"
    MYSQL_PASSWORD          = random_password.db_password.result
    REDIS_HOST              = aws_elasticache_replication_group.redis.primary_endpoint_address
    PUBLIC_BASE_URL         = local.public_base_url
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "random_password" "app_secret" {
  length  = 64
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ALB ingress"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "EC2 app host ingress from ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  dynamic "ingress" {
    for_each = var.ssh_ingress_cidr == "" ? [] : [var.ssh_ingress_cidr]

    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "RDS MySQL ingress from app hosts"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "ElastiCache Redis ingress from app hosts"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 14 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 14
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_db_subnet_group" "mysql" {
  name       = "${local.name}-mysql"
  subnet_ids = aws_subnet.public[*].id
}

resource "aws_db_parameter_group" "mysql" {
  name   = "${local.name}-mysql"
  family = "mysql8.0"

  parameter {
    name  = "require_secure_transport"
    value = "ON"
  }
}

resource "aws_db_instance" "mysql" {
  identifier = "${local.name}-mysql"

  engine         = "mysql"
  engine_version = var.mysql_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = max(var.db_allocated_storage, 100)
  storage_encrypted     = true

  db_name  = "workforceiq"
  username = "workforceiq"
  password = random_password.db_password.result
  port     = 3306

  db_subnet_group_name   = aws_db_subnet_group.mysql.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.mysql.name

  backup_retention_period = var.rds_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  multi_az                     = var.rds_multi_az
  publicly_accessible          = false
  deletion_protection          = var.deletion_protection
  skip_final_snapshot          = var.skip_final_snapshot
  final_snapshot_identifier    = var.skip_final_snapshot ? null : "${local.name}-mysql-final-${random_id.suffix.hex}"
  auto_minor_version_upgrade   = true
  copy_tags_to_snapshot        = true
  apply_immediately            = true
  performance_insights_enabled = var.rds_performance_insights_enabled
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = aws_subnet.public[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = substr("${local.name}-redis", 0, 40)
  description          = "WorkforceIQ Redis for caching, rate limits, and Celery"

  engine         = "redis"
  engine_version = var.redis_engine_version
  node_type      = var.redis_node_type
  port           = 6379

  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  apply_immediately = true
}

resource "aws_s3_bucket" "backups" {
  bucket = "${local.name}-backups-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire-app-json-backups"
    status = "Enabled"

    filter {
      prefix = "json/"
    }

    expiration {
      days = var.backup_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.backup_retention_days
    }
  }
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app-env"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = jsonencode(local.app_env)
}

resource "aws_iam_role" "app" {
  name               = "${local.name}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "app" {
  name = "${local.name}-runtime"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:DescribeImages",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = aws_ecr_repository.app.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.app.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.backups.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.backups.arn}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "${local.name}-ec2"
  role = aws_iam_role.app.name
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  associate_public_ip_address = true
  key_name                    = var.ec2_key_name == "" ? null : var.ec2_key_name

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    aws_region         = var.aws_region
    secret_arn         = aws_secretsmanager_secret.app.arn
    ecr_registry       = local.ecr_registry
    docker_compose_b64 = base64encode(file("${path.module}/../app/docker-compose.aws.yml"))
    nginx_conf_b64     = base64encode(file("${path.module}/../app/nginx.conf"))
  })

  user_data_replace_on_change = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted   = true
    volume_size = 30
    volume_type = "gp3"
  }

  depends_on = [
    aws_db_instance.mysql,
    aws_elasticache_replication_group.redis,
    aws_secretsmanager_secret_version.app,
  ]
}

resource "aws_lb" "app" {
  name               = substr("${local.name}-alb", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.deletion_protection
}

resource "aws_lb_target_group" "app" {
  name     = substr("${local.name}-tg", 0, 32)
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/api/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.app.id
  port             = 8080
}

resource "aws_lb_listener" "http" {
  count = var.acm_certificate_arn == "" ? 1 : 0

  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count = var.acm_certificate_arn == "" ? 0 : 1

  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.acm_certificate_arn == "" ? 0 : 1

  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  count = var.alarm_sns_topic_arn == "" ? 0 : 1

  alarm_name          = "${local.name}-alb-unhealthy-hosts"
  alarm_description   = "WorkforceIQ ALB has unhealthy targets."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [var.alarm_sns_topic_arn]

  dimensions = {
    LoadBalancer = aws_lb.app.arn_suffix
    TargetGroup  = aws_lb_target_group.app.arn_suffix
  }
}
