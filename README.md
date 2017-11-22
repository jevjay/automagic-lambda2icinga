
**Automagic-Lambda2Icinga** is [Lambda](https://aws.amazon.com/lambda/details/) based [Icinga2](https://www.icinga.com/products/icinga-2/) monitoring autodiscovery and configuration tools, which simplifies monitoring configuration for your AWS infrastructure. 

This tool uses custom defined YAML templates in order to generate corresponidng Icinga2 object types for the monitored hosts.

Supported Object Types:

* [Endpoint](https://www.icinga.com/docs/icinga2/latest/doc/09-object-types/#endpoint)
* [Host](https://www.icinga.com/docs/icinga2/latest/doc/09-object-types/#host)
* [Service](https://www.icinga.com/docs/icinga2/latest/doc/09-object-types/#service)
* [Zone](https://www.icinga.com/docs/icinga2/latest/doc/09-object-types/#zone)

### Prerequisites

In order to succesfully deploy application, you need to configure additional AWS services.

#### Terraform configuration

_Make sure you have installed [Terraform](https://www.terraform.io/)_

Export environment variables

```
export TF_VAR_access_key=youraccesskey
export TF_VAR_secret_key=yoursecretaccesskey
export TF_VAR_region=yourregion
export TF_VAR_bucket_acl=private/public
export TF_VAR_bucket_name=yourbucketname
export TF_VAR_api_endpoint=icinga2url
export TF_VAR_api_port=icinga2port
export TF_VAR_api_user=icinga2user
export TF_VAR_api_password=icinga2password
```

Move to terraform directory `cd ./terraform`

Run `terraform plan` to preview AWS changes

Run `terraform apply` to deploy AWS changes

#### Manual configuration

* [Create S3 bucket](http://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html) which will be used to store object Yaml templates.
* [Upload templates](http://docs.aws.amazon.com/AmazonS3/latest/user-guide/upload-objects.html) to newly created bucket. Template(s) location should be: ./objecttype/templatename
* [Create Lambda function](http://docs.aws.amazon.com/lambda/latest/dg/with-cloudtrail-example.html) with following settings:
	* Runtime: `Python 3.6`
	* Handler: `index.handler`
	* Timeout: `> 30sec`
	* EC2 State-change trigger:

	```
	{
	  "detail-type": [
	    "EC2 Instance State-change Notification"
	  ],
	  "detail": {
	    "state": [
	      "running",
	      "terminated"
	    ]
	  },
	  "source": [
	    "aws.ec2"
	  ]
	}
	```

	* Tag change trigger:

	```
	{
	  "detail-type": [
	    "AWS API Call via CloudTrail"
	  ],
	  "detail": {
	    "eventName": [
	      "CreateTags",
	      "DeleteTags"
	    ],
	    "eventSource": [
	      "ec2.amazonaws.com"
	    ]
	  },
	  "source": [
	    "aws.ec2"
	  ]
	}
	```

	* Execution role:

	```
	{
	    "Version": "2012-10-17",
	    "Statement": [
	        {
	            "Sid": "",
	            "Effect": "Allow",
	            "Action": "logs:*",
	            "Resource": "*"
	        },
	        {
	            "Sid": "",
	            "Effect": "Allow",
	            "Action": "ec2:Describe*",
	            "Resource": "*"
	        },
	        {
	            "Sid": "",
	            "Effect": "Allow",
	            "Action": [
	                "s3:ListObjects",
	                "s3:ListBucket",
	                "s3:GetObject"
	            ],
	            "Resource": [
	                "arn:aws:s3:::{yourbucketname}/*",
	                "arn:aws:s3:::{yourbucketname}"
	            ]
	        }
	    ]
	}
	```

	* Environment variables:

	```
	TEMPLATES_BUCKET - Bucket name, configured earlied to store object templates (Required)
	API_USER - Icinga2 API username (Required)
	API_PASS - Icinga2 API password (Required)
	API_ENDPOIN - Icinga2 endpoint url (Required)
	API_PORT - Icinga2 port (Optional. Defaults to: 5665)
	```

### Usage

In order to configure EC2 instance to be auto-discovered and condfigured via Lambda2Icinga function, it needs to be tagged accordingly.

The minumum requred tag is:

* lambda2icinga: enabled/Enabled/True/true (one of these values)

By supplying following tag, Lambda2Icinga function will configure monitoring with default templates. If you want to use your own defined templates first you have to upload them to the template bucket.
You can reference your template by using following tags:

* l2i_host_template: your_host_template_name
* l2i_service_template: your_service_template_name
* l2i_endpoint_template: your_endpoint_template_name
* l2i_zone_template: your_zone_template_name

Configuring host for the first time will downtime its host check for 10 min in order to avoid 'false-positive' alerts (in case host bootstrap is not finished)

Note: This function does not provide functionality to establish API connection between Icinga2 master/client. Please refer to Icinga2 documentation on ["Distributed monitoring"](https://www.icinga.com/docs/icinga2/latest/doc/06-distributed-monitoring/) in order to achieve that.

### TO-DOs

* Add ability to reconfigure host monitoring after uploading new version of used template(s)
* Add ability to configure "global" Icinga2 objects
* Add ability to configure following Icinga2 objects:
	* ApiUser
    * CheckCommand
    * Comment
    * Dependency
    * Downtime
    * ElasticsearchWriter
    * EventCommand
    * FileLogger
    * GelfWriter
    * GraphiteWriter
    * HostGroup
    * IdoMySqlConnection
    * IdoPgsqlConnection
    * InfluxdbWriter
    * Notification
    * NotificationCommand
    * NotificationComponent
    * OpenTsdbWriter
    * PerfdataWriter
    * ScheduledDowntime
    * ServiceGroup
    * StatusDataWriter
    * SyslogLogger
    * TimePeriod
    * User
    * UserGroup
* Add ability to configure Icinga2 agent via SSH
	* Master setup
	* Client setup
* Add ability to configure API connection between client/master

### License

This project is licensed under the MIT License - see the LICENSE file for details
