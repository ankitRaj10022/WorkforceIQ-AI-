resource "aws_db_subnet_group" "mysql" {
  name       = "${local.name}-mysql"
  subnet_ids = aws_subnet.data[*].id
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
  subnet_ids = aws_subnet.data[*].id
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
