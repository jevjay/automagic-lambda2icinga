resource "aws_cloudwatch_event_rule" "ec2_startup" {
  name        = "capture-ec2-start-up"
  description = "Capture each AWS EC2 Start-Up"

  event_pattern = <<PATTERN
{
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "EC2 Instance State-change Notification"
  ],
  "detail": {
    "state": [
      "running"
    ]
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "automagic_lambda2icinga" {
  rule = "${aws_cloudwatch_event_rule.ec2_startup.name}"
  arn  = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}

resource "aws_lambda_permission" "automagic_lambda2icinga_trigger" {
  statement_id  = "AllowExecutionFromCloudWatchEc2StartEvent"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_startup.arn}"
}
