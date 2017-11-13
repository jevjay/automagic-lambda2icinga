variable "automagic_lambda2icinga_package" {
  default = "../src/pkg/bundle.zip"
}

data "aws_iam_policy_document" "lambda2icinga_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda2icinga_assume_role" {
  name               = "lambda2icinga_assume_role"
  assume_role_policy = "${data.aws_iam_policy_document.lambda2icinga_assume_role.json}"
}

data "aws_iam_policy_document" "automagic_lambda2icinga" {
  statement {
    actions = [
      "logs:*",
    ]

    resources = [
      "*",
    ]
  }

  statement {
    actions = [
      "ec2:Describe*",
    ]

    resources = [
      "*",
    ]
  }

  statement {
    actions = [
      "s3:GetObject",
      "s3:ListObjects",
      "s3:ListBucket",
    ]

    resources = [
      "${aws_s3_bucket.s3_tpl_store.arn}",
      "${aws_s3_bucket.s3_tpl_store.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "automagic_lambda2icinga" {
  name = "automagic_lambda2icinga"
  role = "${aws_iam_role.lambda2icinga_assume_role.id}"

  policy = "${data.aws_iam_policy_document.automagic_lambda2icinga.json}"
}

resource "aws_lambda_function" "automagic_lambda2icinga" {
  filename         = "${var.automagic_lambda2icinga_package}"
  function_name    = "automagic_lambda2icinga"
  role             = "${aws_iam_role.lambda2icinga_assume_role.arn}"
  handler          = "index.handler"
  source_code_hash = "${base64sha256(file("${var.automagic_lambda2icinga_package}"))}"
  runtime          = "python3.6"
  timeout          = 90

  environment {
    variables = {
      TEMPLATES_BUCKET = "${var.bucket_name}"
      API_ENDPOINT     = "ec2-52-17-166-42.eu-west-1.compute.amazonaws.com"
      API_PORT         = "5665"
      API_USER         = "root"
      API_PASS         = "4d9RpA5HdH9R54wQ"
    }
  }
}
