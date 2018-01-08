"""
    Application to managae Icinga2 monitoring configuration for clients as
    well as provides ability to configure multiple Icinga2 objects based
    on the YAML templates.

    Variables:
        TEMPLATES_BUCKET - S3 buckets storing user defined Icinga2 objects
                           YAML templates
        API_USER - Icinga2 API user
        API_PASS - Icinga2 API password
        API_PORT - Icinga2 API port
        API_ENDPOINT - Icinga2 API endpoint
"""
from os import environ
import logging
import json
import boto3

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


def invoke_lambda(func_name,
                  payload):
    """
        Calls specified Lambda function
    """
    client = boto3.client('lambda')
    client.invoke(FunctionName=func_name,
                  InvocationType='Event',
                  LogType='None',
                  Payload=json.dumps(payload))


def handler(event, context):
    """
        AWS Lambda main method
    """
    LOGGER.info("Event: \n" + str(event))
    LOGGER.info("Context: \n" + str(context))
    generator_func = env_var('GENERATOR_FUNCTION')
    publisher_func = env_var('PUBLISER_FUNCTION')
    if event['source'] == 'lamda2icinga.agent':
        if event['type'] == 'update_monitoring':
            invoke_lambda(generator_func,
                          event['data'])
        elif event['type'] == 'delete_monitoring':
            invoke_lambda(publisher_func,
                          event['data'])
    elif event['source'] == 'aws.ec2':
        if event['detail-type'] == 'EC2 Instance State-change Notification':
            if event['detail']['state'] == 'terminated':
                instance_id = event['detail']['instance-id']
                payload = {}
                payload['type'] = 'delete_monitoring'
                payload['pkg_name'] = instance_id
                log_msg = "Instance {0} was terminated. Removing from Icinga2...".format(instance_id)
                LOGGER.info(log_msg)
                invoke_lambda(publisher_func,
                              payload)
