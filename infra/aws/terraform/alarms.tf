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
