"""

"""
from os import environ
import logging
import boto3
import json
from botocore.errorfactory import ClientError
from jinja2 import Environment

# Configure LOGGER object
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def env_var(env_name):
    """
        Checks if environment variable is set
        In case it is, returns its value
    """
    try:
        env_var = environ[env_name]
        return env_var
    except KeyError:
        LOGGER.error('Please set the enviroment variable "{0}"'.format(env_name))
        raise


def get_conf_template(bucket, key):
    """
        Read S3 object and return its stored data
    """
    client = boto3.client('s3')
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()
    except ClientError as err:
        if err.response['Error']['Code'] == "NoSuchKey":
            # Log missing template 'fallback' operation
            LOGGER.warning("Can not find template: \n{0}".format(key))


def generate_configuration_object(template, data):
    """
        Generate Icinga2 configuration file out of the template
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(template).render(data=data)


def call_publisher(func_name, configs):
    """
        Calls Lambda function
    """
    # Build payload
    payload = {
        'objetcs': configs,
    }
    client = boto3.client('lambda')
    client.invoke(FunctionName='LambdaWorker',
                  InvocationType='Event',
                  LogType='None',
                  Payload=json.dumps(payload))


def handler(event, context):
    """
        AWS Lambda main method
    """
    # Get environment variables
    template_bucket = env_var('TEMPLATES_BUCKET')
    publisher_func = env_var('PUBLISER_FUNCTION')
    # Get all used templates
    templates = event['templates']
    configs = {}
    for template in templates:
        template = get_conf_template(template_bucket, template['key'])
        config = generate_configuration_object(template, template['data'])
        # Get object type
        object_type = template['key'].split('/')[0]
        configs[object_type] = config
    # Call publisher function
    call_publisher(publisher_func, configs)
