variable "bucket_name" {}

variable "bucket_acl" {}

resource "aws_s3_bucket" "s3_tpl_store" {
  bucket = "${var.bucket_name}"
  acl    = "${var.bucket_acl}"

  tags {
    Name = "${var.bucket_name}"
  }
}
