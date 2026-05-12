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
    DATABASE_URL            = "mysql+pymysql://workforceiq:${random_password.mysql_password.result}@mysql:3306/workforceiq"
    REDIS_URL               = "redis://redis:6379/0"
    CELERY_BROKER_URL       = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND   = "redis://redis:6379/0"
    WEB_CONCURRENCY         = "2"
    GUNICORN_THREADS        = "2"
    CELERY_CONCURRENCY      = "1"
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
    WORKFORCEIQ_IMAGE       = local.image_uri
    MYSQL_ROOT_PASSWORD     = random_password.mysql_root_password.result
    MYSQL_PASSWORD          = random_password.mysql_password.result
  }
}

resource "random_password" "app_secret" {
  length  = 64
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "mysql_root_password" {
  length  = 32
  special = false
}

resource "random_password" "mysql_password" {
  length  = 32
  special = false
}

resource "aws_vpc" "main" {
  cidr_block           = "10.52.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.52.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
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
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "Free-tier single-host WorkforceIQ stack"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
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
        description  = "Keep only the latest image to stay inside free storage limits"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_iam_role" "app" {
  name               = "${local.name}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "ecr_pull" {
  name = "${local.name}-ecr-pull"
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
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  associate_public_ip_address = true
  key_name                    = var.ec2_key_name == "" ? null : var.ec2_key_name

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    aws_region            = var.aws_region
    ecr_registry          = local.ecr_registry
    docker_compose_b64    = base64encode(file("${path.module}/../app/docker-compose.free.yml"))
    nginx_conf_b64        = base64encode(file("${path.module}/../app/nginx.conf"))
    env_file_b64          = base64encode(join("\n", [for key, value in local.app_env : "${key}=${value}"]))
    backup_retention_days = var.backup_retention_days
  })

  user_data_replace_on_change = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted   = true
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }
}
