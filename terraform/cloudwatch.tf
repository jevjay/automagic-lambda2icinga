# === Cloudwatch event: instance startup ===
resource "aws_cloudwatch_event_rule" "ec2_startup" {
  name        = "capture-ec2-start"
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

resource "aws_cloudwatch_event_target" "ec2_startup" {
  rule = "${aws_cloudwatch_event_rule.ec2_startup.name}"
  arn  = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}

resource "aws_lambda_permission" "ec2_startup_trigger" {
  statement_id  = "AllowExecCloudWatchEc2StartEvent"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_startup.arn}"
}

# === Cloudwatch event: instance tag creation ===
resource "aws_cloudwatch_event_rule" "ec2_tag_create" {
  name        = "capture-ec2_tag_create"
  description = "Capture each AWS EC2 Tag Creation"

  event_pattern = <<PATTERN
{
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com"
    ],
    "eventName": [
      "CreateTags"
    ]
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "ec2_tag_create" {
  rule = "${aws_cloudwatch_event_rule.ec2_tag_create.name}"
  arn  = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}

resource "aws_lambda_permission" "ec2_tag_create_trigger" {
  statement_id  = "AllowExecutionFromCloudWatchEc2StartEvent"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_tag_create.arn}"
}
