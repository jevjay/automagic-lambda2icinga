resource "aws_cloudwatch_event_rule" "ec2_startup" {
  name        = "capture-ec2-start-up"
  description = "Capture each AWS EC2 Start-Up"

  event_pattern = <<PATTERN
{
  "detail-type": "Capture each AWS EC2 Start-Up",
  "source": "aws.ec2",
  "account": "${var.account}",
  "region": "${var.region}",
  "resources": [
    "arn:aws:ec2:${var.region}:%{var.account}:instance/*"
  ],
  "detail":{
      "state":"running"
   }
}
PATTERN
}

resource "aws_cloudwatch_event_target" "automagic_lambda2icinga" {
  rule      = "${aws_cloudwatch_event_rule.ec2_startup.name}"
  arn       = "${aws_lambda_function.automagic_lambda2icinga.arn}"
}
