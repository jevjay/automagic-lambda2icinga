variable "automagic_lambda2icinga_package" {
  default = "../src/pkg/bundle.zip"
}

data "aws_iam_policy_document" "lambda_assume_role" {
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

resource "aws_iam_role" "lambda_assume_role" {
  name               = "lambda_assume_role"
  assume_role_policy = "${data.aws_iam_policy_document.lambda_assume_role.json}"
}

resource "aws_lambda_function" "automagic_lambda2icinga" {
  filename         = "${var.automagic_lambda2icinga_package}"
  function_name    = "automagic_lambda2icinga"
  role             = "${aws_iam_role.lambda_assume_role.arn}"
  handler          = "index.handler"
  source_code_hash = "${base64sha256(file("${var.automagic_lambda2icinga_package}"))}"
  runtime          = "python3.6"

  environment {
    variables = {
      TEMPLATES_BUCKET = "${var.bucket_name}"
    }
  }
}
