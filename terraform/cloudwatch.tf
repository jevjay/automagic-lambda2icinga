# === Cloudwatch event: instance startup ===
resource "aws_cloudwatch_event_rule" "ec2_states" {
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
      "running",
      "terminated"
    ]
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "ec2_states" {
  rule = "${aws_cloudwatch_event_rule.ec2_states.name}"
  arn  = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}

resource "aws_lambda_permission" "ec2_states_trigger" {
  statement_id  = "AllowExecCloudWatchEc2StartEvent"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_states.arn}"
}

# === Cloudwatch event: instance tag creation ===
resource "aws_cloudwatch_event_rule" "ec2_tag_actions" {
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
      "CreateTags",
      "DeleteTags"
    ]
  }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "ec2_tag_actions" {
  rule = "${aws_cloudwatch_event_rule.ec2_tag_actions.name}"
  arn  = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}

resource "aws_lambda_permission" "ec2_tag_actions_trigger" {
  statement_id  = "AllowExecutionFromCloudWatchEc2StartEvent"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_tag_actions.arn}"
}

# === S3 Template updated Lambda trigger
resource "aws_lambda_permission" "template_bucket_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.automagic_lambda2icinga.arn}"
  principal     = "s3.amazonaws.com"
  source_arn    = "${aws_s3_bucket.s3_tpl_store.arn}"
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = "${aws_s3_bucket.s3_tpl_store.id}"

  lambda_function {
    lambda_function_arn = "${aws_lambda_function.automagic_lambda2icinga.arn}"
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }
}
