variable "bucket_name" {}

variable "bucket_acl" {}

# S3 bucket to store lambda2icinga confifuration templates
resource "aws_s3_bucket" "s3_tpl_store" {
  bucket = "${var.bucket_name}"
  acl    = "${var.bucket_acl}"

  tags {
    Name = "${var.bucket_name}"
  }
}

# Create default lambda2icinga configuration templates
# Default host template
resource "aws_s3_bucket_object" "default_host_tpl" {
  bucket = "${var.bucket_name}"
  key    = "host/default"
  source = "../templates/host/default.yaml"
  etag   = "${md5(file("../templates/host/default.yaml"))}"
}

# Default service template
resource "aws_s3_bucket_object" "default_service_tpl" {
  bucket = "${var.bucket_name}"
  key    = "service/default"
  source = "../templates/service/default.yaml"
  etag   = "${md5(file("../templates/service/default.yaml"))}"
}
