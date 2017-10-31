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
import sys
import logging
from datetime import datetime, timedelta
import calendar
import json
import boto3
from botocore.errorfactory import ClientError
import yaml
import requests
from jinja2 import Environment

# Configure LOGGER object
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def get_instance_data(instance):
    """
        Get EC2 instances accross region
    """
    # Get EC2 resource
    ec2 = boto3.client('ec2', region_name=os.environ['AWS_DEFAULT_REGION'])
    # Get EC2 resource
    ec2 = boto3.client('ec2', region_name=os.environ['AWS_DEFAULT_REGION'])
    ec2_filters = [{
        "Name": "tag:icinga2",
        "Values": ["enabled", "True", "true"]
        },
        {"Name": "instance-id", "Values": [instance]}]
    response = ec2.describe_instances(Filters=ec2_filters)
    data = response['Reservations'][0]['Ínstances'][0]
    # Flag to configure instance with public ip
    public = False
    metadata = {}
    # Set default host/service configuration templates
    metadata['l2i_host_template'] = 'default'
    metadata['l2i_service_template'] = 'default'
    for tag in data['Tags']:
        # Get hostname
        if tag['Key'] == 'Name':
            metadata['hostname'] = tag['Value']
        # Get host configuration template
        if tag['Key'] == 'l2i_host_template':
            metadata['l2i_host_template'] = tag['Value']
        # Get service configuration template
        if tag['Key'] == 'l2i_service_template':
            metadata['l2i_service_template'] = tag['Value']
        # Check if instance marked to be configured with pub ip
        if tag['Key'] = 'l2i_public_enabled':
            public = True

    # Assign private ip
    metadata['address'] = data['PrivateIpAddress']
    # If public flag set to true, enable public ip
    if public:
        try:
            metadata['address'] = data['PublicIpAddress']
        except KeyError:
            # Add error logging and kepp private ip
            pass
    return metadata


def get_conf_template(bucket, key):
    """
        Read S3 object and return its stored data
    """
    client = boto3.client('s3')
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()
    except ClientError as err:
        if err.response['Error']['Code'] == "404":
            # Log missing template 'fallback' operation
            msg = "Templdate {0} does not exist. Using 'default' template".format(key)
            LOGGER.warning(msg)
            # Retrieve default template
            key = "{0}/default".format(key.split('/')[0])
            obj = client.get_object(Bucket=bucket, Key=key)
            return obj['Body'].read()
        else:
            LOGGER.error("Unhandled error: \n{0}").format(err)
            sys.exit(1)


def generate_zone_configuration(template):
    """
    Generates Icinga2 zone configuration file from the template
    Zone object params:
    - endpoints: Array of endpoint names located in this zone
    - parent: The name of the parent zone
    - global: flag to sync confgiuration files across all nodes within zone
    """
    conf = """
    {% for zone in template %}
    object Zone "{{ zone.name }}" {
        endpoints = [ "{{ zone.name }}" ]
        {% if zone.parent is not None %}
        parent = "{{ zone.parent }}"
        {% endif %}
        {% if zone.global %}
        global = "true"
        {% endif %}
    }\n
    {% endfor %}
    """
    return Environment().from_string(conf).render(template=template)


def generate_endpoint_configuration(template):
    """
    Generates Icinga2 endpoing configuration file from the template
    Endpoint object params:
    - host: The hostname/IP address of the remote Icinga 2 instance.
    - port: The service name/port of the remote Icinga 2 instance.
    - log_duration: Duration for keeping replay logs on connection loss.
    """
    conf = """
    {% for endpoint in template %}
    object Endpoint "{{ endpoint.name }}" {
        {% if endpoint.host is not None %}
        host = "{{ endpoint.host }}"
        {% endif %}
        {% if endpoint.port is not None %}
        port = "{{ endpoint.port }}"
        {% endif %}
        {% if endpoint.log_duration is not None %}
        log_duration = {{ endpoint.log_duration }}
        {% endif %}
    }\n
    {% endfor %}
    """
    return Environment().from_string(conf).render(template=template)


def generate_host_configuration(data, template):
    """
    Genearates Icinga2 host configuration file out from the template
    Host object params:
    - display_name: A short description of the host
    - address: The host’s address.
    - groups: A list of host groups this host belongs to.
    - vars: A dictionary containing custom attributes for this host.
    - check_command: The name of the check command.
    - max_check_attempts: The number of times a host is re-checked before
    changing into a hard state.
    - check_period: The name of a time period which determines when this host
    should be checked. Not set by default.
    - check_timeout: Check command timeout in seconds. Overrides the
    CheckCommand’s timeout attribute.
    - check_interval: The check interval (in seconds). This interval is used
    for checks when the host is in a HARD state.
    - retry_interval: The retry interval (in seconds). This interval is used
    for checks when the host is in a SOFT state.
    - enable_notifications: Whether notifications are enabled.
    - enable_active_checks: Whether active checks are enabled.
    - enable_passive_checks: Whether passive checks are enabled.
    - enable_event_handler: Enables event handlers for this host.
    - enable_flapping: Whether flap detection is enabled.
    - enable_perfdata: Whether performance data processing is enabled.
    - event_command: The name of an event command that should be executed every
    time the host’s state changes or the host is in a SOFT state.
    - flapping_threshold: The flapping threshold in percent when a host is
    considered to be flapping.
    - volatile: The volatile setting enables always HARD state types if NOT-OK
    state changes occur.
    - zone: The zone this object is a member of.
    - command_endpoint: The endpoint where commands are executed on.
    - notes: Notes for the host.
    - notes_url: Url for notes for the host
    - action_url: Url for actions for the host
    - icon_image: Icon image for the host.
    Used by external interfaces only.
    - icon_image_alt Icon image description for the host.
    Used by external interface only.
    """
    conf = """
    object Host "{{ data.hostname }}" {
        address = "{{ data.address }}"
        {% if template.check_command is not None %}
        check_command = "{{ template.check_command }}"
        {% else %}
        check_command = "hostalive"
        {% endif %}
        {% if template.display_name is not None %}
        display_name = "{{ template.display_name }}"
        {% else %}
        display_name = "{{ data.fqnd }}"
        {% endif %}
        {% if template.groups is not None %}
        groups = [{% for group in template.groups %}"{{ group }}",{% endfor %}]
        {% endif %}
        {% if template.vars is not None %}
        {% for key, value in template.vars.iteritems() %}
        vars.{{ key }} = "{{ value }}"
        {% endfor %}
        {% endif %}
        {% if template.max_check_attempts is not None %}
        max_check_attempts = "{{ template.max_check_attempts }}"
        {% endif %}
        {% if template.check_period is not None %}
        check_period = "{{ template.check_period }}"
        {% endif %}
        {% if template.check_timeout is not None %}
        check_timeout = "{{ template.check_timeout }}"
        {% endif %}
        {% if template.check_interval is not None %}
        check_interval = "{{ template.check_interval }}"
        {% endif %}
        {% if template.retry_interval is not None %}
        retry_interval = "{{ template.retry_interval }}"
        {% endif %}
        {% if template.enable_notifications is not None %}
        enable_notifications = "{{ template.enable_notifications }}"
        {% endif %}
        {% if template.enable_active_checks is not None %}
        enable_active_checks = "{{ template.enable_active_checks }}"
        {% endif %}
        {% if template.enable_passive_checks is not None %}
        enable_passive_checks = "{{ template.enable_passive_checks }}"
        {% endif %}
        {% if template.enable_event_handler is not None %}
        enable_event_handler = "{{ template.enable_event_handler }}"
        {% endif %}
        {% if template.enable_flapping is not None %}
        enable_flapping = "{{ template.enable_flapping }}"
        {% endif %}
        {% if template.enable_perfdata is not None %}
        enable_perfdata = "{{ template.enable_perfdata }}"
        {% endif %}
        {% if template.event_command is not None %}
        event_command = "{{ template.event_command }}"
        {% endif %}
        {% if template.volatile is not None %}
        volatile = "{{ template.volatile }}"
        {% endif %}
        {% if template.zone is not None %}
        zone = "{{ template.zone }}"
        {% endif %}
        {% if template.command_endpoint is not None %}
        command_endpoint = "{{ template.command_endpoint }}"
        {% endif %}
        {% if template.notes is not None %}
        notes = "{{ template.notes }}"
        {% endif %}
        {% if template.notes_url is not None %}
        notes_url = "{{ template.notes_url }}"
        {% endif %}
        {% if template.action_url is not None %}
        action_url = "{{ template.action_url }}"
        {% endif %}
        {% if template.icon_image is not None %}
        icon_image = "{{ template.icon_image }}"
        {% endif %}
        {% if template.icon_image_alt is not None %}
        icon_image_alt = "{{ template.icon_image_alt }}"
        {% endif %}
    }

    """
    return Environment().from_string(conf).render(data=data,
                                                  template=template)


def generate_service_configuration(data, template):
    """

    """
    conf = """
    object Service "{{ template.servicename }}" {
        host_name = "{{ data.hostname }}"
        {% if template.display_name is not None %}
        display_name = "{{ template.display_name }}"
        {% endif %}
        {% if template.groups in not None %}
        groups = [{% for group in template.groups %}"{{ group }}",{% endfor %}]
        {% endif %}
        {% if template.max_check_attempts is not None %}
        max_check_attempts = "{{ template.max_check_attempts }}"
        {% endif %}
        {% if template.check_command is not None %}
        check_command = "{{ template.check_command }}"
        {% endif %}
        {% if template.vars is not None %}
        {% for key, value in template.vars.iteritems() %}
        vars.{{ key }} = "{{ value }}"
        {% endfor %}
        {% endif %}
        {% if template.check_period is not None %}
        check_period = "{{ template.check_period }}"
        {% endif %}
        {% if template.check_timeout is not None %}
        check_timeout = "{{ template.check_timeout }}"
        {% endif %}
        {% if template.check_interval is not None %}
        template.check_interval = "{{ template.check_interval }}"
        {% endif %}
        {% if template.retry_interval is not None %}
        retry_interval = "{{ template.retry_interval }}"
        {% endif %}
        {% if template.enable_notifications is not None%}
        enable_notifications = "{{ template.enable_notifications }}"
        {% endif %}
        {% if template.enable_active_checks is not None %}
        enable_active_checks = "{{ template.enable_active_checks }}"
        {% endif %}
        {% if template.enable_passive_checks is not None %}
        enable_passive_checks = "{{ template.enable_passive_checks }}"
        {% endif %}
        {% if template.enable_event_handler is not None %}
        enable_event_handler = "{{ template.enable_event_handler }}"
        {% endif %}
        {% if template.enable_flapping is not None %}
        enable_flapping = "{{ template.enable_flapping }}"
        {% endif %}
        {% if template.enable_perfdata is not None %}
        enable_perfdata = "{{ template.enable_perfdata }}"
        {% endif %}
        {% if template.event_command is not None %}
        event_command = "{{ template.event_command }}"
        {% endif %}
        {% if template.flapping_threshold is not None %}
        flapping_threshold = "{{ template.flapping_threshold }}"
        {% endif %}
        {% if template.volatile is not None %}
        volatile = "{{ template.volatile }}"
        {% endif %}
        {% if template.zone is not None %}
        zone = "{{ template.zone }}"
        {% endif %}
        {% if template.command_endpoint is not None %}
        command_endpoint = "{{ template.command_endpoint }}"
        {% endif %}
        {% if template.notes is not None %}
        notes = "{{ template.notes }}"
        {% endif %}
        {% if template.notes_url is not None %}
        notes_url = "{{ template.notes_url }}"
        {% endif %}
        {% if template.action_url is not None %}
        action_url = "{{ template.action_url }}"
        {% endif %}
        {% if template.icon_image is not None %}
        icon_image = "{{ template.icon_image }}"
        {% endif %}
        {% if template.icon_image_alt is not None %}
        icon_image_alt = "{{ template.icon_image_alt }}"
        {% endif %}
    }

    """
    return Environment().from_string(conf).render(data=data,
                                                  template=template)


def get_api_request(url,
                    user,
                    password,
                    ssl_verify=False):
    '''
      Verify Icinga 2 object configuration existatnce
    '''
    if url is None:
        LOGGER.error("FAIL: Icinga2 URL is missing")
    elif user is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    elif password is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    else:
        try:
            response = requests.get(url,
                                    auth=(user, password),
                                    verify=ssl_verify)
        except requests.exceptions.Timeout:
            LOGGER.error("Request to %s has timed out.", url)
            # Maybe set up for a retry, or continue in a retry loop
        except requests.exceptions.TooManyRedirects:
            LOGGER.error("Request to %s results in too many redirects.", url)
        # Tell the user their URL was bad and try a different one
        except requests.exceptions.RequestException as err:
            # catastrophic error. bail.
            LOGGER.error(err)
            sys.exit(1)
        response_data = response.json()
        results = response_data['results']
        print(results)
        if results:
            return True
        return False


def post_api_request(url,
                     user,
                     password,
                     data=None,
                     ssl_verify=False):
    '''
      Cretate (PUT) configuration files to Icinga2 master
    '''
    if url is None:
        LOGGER.error("FAIL: Icinga2 URL is missing")
    elif user is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    elif password is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    else:
        headers = {'Accept': 'application/json'}
        try:
            if data is not None:
                response = requests.post(url,
                                         auth=(user, password),
                                         headers=headers,
                                         verify=ssl_verify)
            else:
                response = requests.post(url,
                                     auth=(user, password),
                                     headers=headers,
                                     data=json.dumps(data),
                                     verify=ssl_verify)
        except requests.exceptions.Timeout:
            LOGGER.error("Request to %s has timed out.", url)
        # Maybe set up for a retry, or continue in a retry loop
        except requests.exceptions.TooManyRedirects:
            LOGGER.error("Request to %s results in too many redirects.", url)
        # Tell the user their URL was bad and try a different one
        except requests.exceptions.RequestException as err:
            # catastrophic error. bail.
            LOGGER.error(err)
            sys.exit(1)
        response_data = response.json()
        results = response_data['results']
        print(results)


def handler(event, context):
    """
        AWS Lambda main method
    """
    template_bucket = environ['TEMPLATES_BUCKET']
    api_user = environ['API_USER']
    api_pass = environ['API_PASS']
    api_port = environ['API_PORT']
    api_endpoint = environ['API_ENDPOINT']

    # Get instance metadata
    metadata = get_instance_data(event['detail']['instance-id'])

    templates = {}
    templates['host'] = "host/{0}".format(metadata['l2i_host_template'])
    templates['service'] = "service/{0}".format(metadata['l2i_service_template'])

    # Retrieve host configuration template from template store (S3 bucket)
    host_conf_tpl = get_conf_template(template_bucket,
                                      templates['host'])
    # Retrieve service configuration template from template store (S3 bucket)
    service_conf_tpl = get_conf_template(template_bucket,
                                         templates['service'])
    # Step 1: Check if configuration package exist
    base_url = "https://{0}:{1}/v1/config/packages".format(api_endpoint, api_port)
    packages = get_api_request(base_url, api_user, api_pass)
    # check if package for the host exist
    stages = None
    for package in packages:
        if package['name'] == metadata['hostname']:
            stages = package['stages']
            break
    uri = base_url + "/{0}".format(metadata['hostname'])
    # if stages exist, confugration package was created
    # otherwise create new configuration package
    if stages is not None:
        post_api_request(uri, api_user, api_pass)

    # Generate host configuration content
    host_conf = generate_host_configuration(metadata, yaml.load(host_conf_tpl))
    # Create host configuration stage
    if host_conf is not None:
        data = {}
        conf_path = 'conf.d/{0}.conf'.format(metadata['hostname'])
        data['files'] = {conf_path: host_conf}
        post_api_request(uri, api_user, api_pass, data)
        # Downtime just created host check
        downtime_uri = "https://{0}:{1}/v1/actions/schedule-downtime?type=Host&filter=host.name=={3}".format(api_endpoint,
                                                                                                             api_port,
                                                                                                             metadata['hostname'])
        downtime_data = {}
        now = datetime.utcnow()
        downtime_time['start_time'] = calendar.timegm(now.utctimetuple())
        end_timestamp = datetime.utcnow() + datetime.timedelta(minutes=10)
        downtime_time['end_time'] = calendar.timegm(end_timestamp.timetuple())

        post_api_request(downtime_uri,
                         api_user,
                         api_pass,
                         downtime_data)

    # Generate service configurations
    services = yaml.load(service_conf_tpl)
    service_conf = None
    for service in services:
        service_conf += generate_service_configuration(metadata, service)
    # Create host service configuration file
    if service_conf is not None:
        data = {}
        conf_path = 'conf.d/{0}_services.conf'.format(metadata['hostname'])
        data['files'] = {conf_path: service_conf}
        post_api_request(uri, api_user, api_pass, data)
