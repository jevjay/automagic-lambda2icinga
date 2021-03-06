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


def get_instance_data(ec2_filter):
    """
        Get EC2 instances accross region
    """
    # Get EC2 resource
    ec2 = boto3.client('ec2', region_name=environ['AWS_DEFAULT_REGION'])
    response = ec2.describe_instances(Filters=ec2_filter)
    LOGGER.info(response)
    try:
        #data = response['Reservations'][0]['Instances'][0]
        reservations = response['Reservations']
    except IndexError:
        err_msg = "Unable to retrieve instance data. Aborting..."
        LOGGER.error(err_msg)
        sys.exit(1)
    data = []
    for reservation in reservations:
        # Flag to configure instance with public ip
        metadata = {}
        # Set default host/service configuration templates
        metadata['l2i_host_template'] = 'default'
        metadata['l2i_service_template'] = 'default'
        metadata['l2i_endpoint_template'] = 'default'
        metadata['l2i_zone_template'] = 'default'
        # Assign private ip
        metadata['address'] = reservation['Instances'][0]['PrivateIpAddress']
        for tag in reservation['Instances'][0]['Tags']:
            # Get hostname
            if tag['Key'] == 'Name':
                metadata['hostname'] = tag['Value']
            # Get host configuration template
            if tag['Key'] == 'l2i_host_template':
                metadata['l2i_host_template'] = tag['Value']
            # Get service configuration template
            if tag['Key'] == 'l2i_service_template':
                metadata['l2i_service_template'] = tag['Value']
            # Get host configuration template
            if tag['Key'] == 'l2i_endpoint_template':
                metadata['l2i_endpoint_template'] = tag['Value']
            # Get service configuration template
            if tag['Key'] == 'l2i_zone_template':
                metadata['l2i_zone_template'] = tag['Value']
            # Check if instance marked to be configured with public endpoint
            # Example: ELB/ALB endpoints, Route53 entry, EC2 public dns name
            if tag['Key'] == 'l2i_public_endpoint':
                metadata['address'] = tag['Value']
        data.append(metadata)
    LOGGER.info(data)
    return data


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


def generate_apiuser_configuration(template):
    """
    Generates Icinga2 ApiUser object, which is used for authentication against
    the Icinga 2 API
    ApiUser object params:
    - password: Password string
    - client_cn: Client Common Name
    - permissions: Array of permissions
    """
    conf = """
    object ApiUser "{{ template.name }}" {
        {% if template.password is defined %}
        password = "{{ template.password }}"
        {% endif %}
        {% if template.client_cn is defined %}
        client_cn = "{{ template.client_cn }}"
        {% endif %}
        {% if template.permissions is defined %}
        permissions = [{% for perm in template.permissions %}"{{ perm }}",{% endfor %}]
        {% else %}
        permissions = [ "*" ]
        {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(template=template)


def generate_checkcommand_configuration(template):
    """
    Generates a check command object definition.
    CheckCommand object params:
    - command: The command. This can either be an array of individual command
               arguments.Alternatively a string can be specified in which case
               the shell interpreter (usually /bin/sh) takes care of parsing
               the command. When using the “arguments” attribute this must be
               an array. Can be specified as function for advanced
               implementations.
    - env: A dictionary of macros which should be exported as environment
           variables prior to executing the command.
    - vars: A dictionary containing custom attributes that are specific to
            this command.
    - timeout: The command timeout in seconds.
    - arguments: A dictionary of command arguments.
    """
    conf = """
    object CheckCommand "{{ template.name }}" {
        command = [ {{ template.command }} ]
        {% if template.env is defined %}
        {% for key, value in template.env.items() %}
        env.{{ key }} = {{ value }}
        {% endfor %}
        {% endif %}
        {% if template.vars is defined %}
        {% for key, value in template.vars.items() %}
        vars.{{ key }} = {{ value }}
        {% endfor %}
        {% endif %}
        {% if template.timeout is defined %}
        timeout = "{{ template.timeout }}"
        {% endif %}
        {% if template.arguments is defined %}
        arguments = {
            {% for key, value in template.arguments.items() %}
            {% if value is mapping %}
            "{{ key }}" = {
                {% for k, v in value.items() %}
                {{ k }} = "{{ v }}"
                {% endfor %}
            }
            {% else %}
            "{{ key }}" = "${{ value }}$"
            {% endif %}
            {% endfor %}
        }
        {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(template=template)


def generate_comment_configuration(template):
    """
    Comments created at runtime are represented as objects
    CheckCommand object params:
    - host_name: The name of the host this comment belongs to
    - service_name: The short name of the service this comment belongs to.
    - author: The author’s name.
    - text: The comment text.
    - entry_time: The UNIX timestamp when this comment was added.
    - entry_type: The comment type
                  (User = 1, Downtime = 2, Flapping = 3, Acknowledgement = 4)
    - expire_time: The comment’s expire time as UNIX timestamp
    - persistent: Only evaluated for entry_type Acknowledgement.
                  true does not remove the comment when the acknowledgement
                  is removed.
    """
    conf = """
    object Comment "{{ template.name }}" {
    host_name = {{ template.host_name }}
    {% if template.service_name is defined %}
    service_name = {{ template.service_name }}
    {% endif %}
    author = {{ template.author }}
    text = {{ template.text }}
    {% if template.entry_time is defined %}
    entry_time = {{ template.entry_time }}
    {% endif %}
    {% if template.entry_type is defined %}
    entry_type = {{ template.entry_type }}
    {% endif %}
    {% if template.expire_time is defined %}
    expire_time = {{ template.expire_time }}
    {% endif %}
    {% if template.persistent is defined %}
    persistent = {{ template.persistent }}
    {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(template=template)


def generate_dependency_configuration(template):
    """
    Generates Dependency objects are used to specify dependencies between
    hosts and services. Dependencies can be defined as:
        Host-to-Host,
        Service-to-Service,
        Service-to-Host,
        Host-to-Service relations.
    Dependency object params:
    - parent_host_name: The parent host.
    - parent_service_name: The parent service. If omitted, this
                           dependency object is treated as host dependency.
    - child_host_name: The child host.
    - child_service_name: The child service. If omitted, this
                          dependency object is treated as host dependency.
    - disable_checks: Whether to disable checks when this dependency fails.
    - disable_notifications: Whether to disable notifications when this
                             dependency fails.
    - ignore_soft_states: Whether to ignore soft states for the reachability
                          calculation.
    - period: Time period object during which this dependency is enabled.
    - states: A list of state filters when this dependency should be OK.
    """
    conf = """
    object Dependency "{{ template.name }}" {
    parent_host_name = "{{ template.parent_host_name }}"
    {% if template.parent_service_name is defined %}
    parent_service_name = "{{ template.parent_service_name }}"
    {% endif %}
    child_host_name = "{{ template.child_host_name }}"
    {% if template.child_service_name is defined %}
    child_service_name = "{{ child_service_name }}"
    {% endif %}
    {% if template.disable_checks is defined %}
    disable_checks = {{ template.disable_checks }}
    {% endif %}
    {% if template.disable_notifications is defined %}
    disable_notifications = {{ template.disable_notifications }}
    {% endif %}
    {% if template.ignore_soft_states is defined %}
    ignore_soft_states = {{ template.ignore_soft_states }}
    {% endif %}
    {% if template.period is defined %}
    period = "{{ template.period }}"
    {% endif %}
    {% if template.states is defined %}
    states = [{% for state in template.states %} {{ state }},{% endfor %}]
    {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(template=template)


def generate_endpoint_configuration(data, template):
    """
    Generates Icinga2 endpoint configuration from the template
    Endpoint object params:
    - host: The hostname/IP address of the remote Icinga 2 instance
    - port: The service name/port of the remote Icinga 2 instance
    - log_duration: Duration for keeping replay logs on connection loss.
    Defaults to 1d (86400 seconds). Attribute is specified in seconds.
    If log_duration is set to 0, replaying logs is disabled.
    """
    conf = """
    object Endpoint "{{ data.hostname }}" {
        host = "{{ data.address }}"
        {% if template.port is defined %}
        port = {{ template.port }}
        {% endif %}
        {% if template.log_duration is defined %}
        log_duration = {{ template.log_duration }}
        {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(data=data,
                                                                    template=template)


def generate_zone_configuration(data, template):
    """
    Generates Icinga2 zone configuration from the template
    Zone objects are used to specify which Icinga 2 instances are located in a zone.
    Zone object params:
    - endpoints: Array of endpoint names located in this zone
    - parent: The name of the parent zone
    """
    conf = """
    object Zone "{{ data.hostname }}" {
        endpoints = [ "{{ data.hostname }}" ]
        {% if template.parent is defined %}
        parent = "{{ template.parent }}"
        {% elif %}
        parent = "master"
        {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(data=data,
                                                                    template=template)


def generate_host_configuration(data, template):
    """
    Genearates Icinga2 host configuration from the template
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
        {% if template.check_command is defined %}
        check_command = "{{ template.check_command }}"
        {% else %}
        check_command = "hostalive"
        {% endif %}
        {% if template.display_name is defined %}
        display_name = "{{ template.display_name }}"
        {% else %}
        {% if data.fqdn is defined %}
        display_name = "{{ data.fqnd }}"
        {% else %}
        display_name = "{{ data.hostname }}"
        {% endif %}
        {% endif %}
        {% if template.groups is defined %}
        groups = [{% for group in template.groups %}"{{ group }}",{% endfor %}]
        {% endif %}
        {% if template.max_check_attempts is defined %}
        max_check_attempts = "{{ template.max_check_attempts }}"
        {% endif %}
        {% if template.check_period is defined %}
        check_period = "{{ template.check_period }}"
        {% endif %}
        {% if template.check_timeout is defined %}
        check_timeout = "{{ template.check_timeout }}"
        {% endif %}
        {% if template.check_interval is defined %}
        check_interval = "{{ template.check_interval }}"
        {% endif %}
        {% if template.retry_interval is defined %}
        retry_interval = "{{ template.retry_interval }}"
        {% endif %}
        {% if template.enable_notifications is defined %}
        enable_notifications = {{ template.enable_notifications|lower }}
        {% endif %}
        {% if template.enable_active_checks is defined %}
        enable_active_checks = {{ template.enable_active_checks|lower }}
        {% endif %}
        {% if template.enable_passive_checks is defined %}
        enable_passive_checks = {{ template.enable_passive_checks|lower }}
        {% endif %}
        {% if template.enable_event_handler is defined %}
        enable_event_handler = "{{ template.enable_event_handler }}"
        {% endif %}
        {% if template.enable_flapping is defined %}
        enable_flapping = {{ template.enable_flapping|lower }}
        {% endif %}
        {% if template.enable_perfdata is defined %}
        enable_perfdata = {{ template.enable_perfdata|lower }}
        {% endif %}
        {% if template.event_command is defined %}
        event_command = "{{ template.event_command }}"
        {% endif %}
        {% if template.volatile is defined %}
        volatile = "{{ template.volatile }}"
        {% endif %}
        {% if template.zone is defined %}
        zone = "{{ template.zone }}"
        {% endif %}
        {% if template.command_endpoint is defined %}
        command_endpoint = "{{ template.command_endpoint }}"
        {% endif %}
        {% if template.notes is defined %}
        notes = "{{ template.notes }}"
        {% endif %}
        {% if template.notes_url is defined %}
        notes_url = "{{ template.notes_url }}"
        {% endif %}
        {% if template.action_url is defined %}
        action_url = "{{ template.action_url }}"
        {% endif %}
        {% if template.icon_image is defined %}
        icon_image = "{{ template.icon_image }}"
        {% endif %}
        {% if template.icon_image_alt is defined %}
        icon_image_alt = "{{ template.icon_image_alt }}"
        {% endif %}
    }

    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(data=data,
                                                                    template=template)


def generate_service_configuration(data, template):
    """
    Genearates Icinga2 service configuration from the template
    Service object params:
    - host_name: The host this service belongs to
    - display_name: A short description of the service
    - groups: The service groups this service belongs to
    - vars: A dictionary containing custom attributes that are specific
    to this service
    - check_command: The name of the check command
    - max_check_attempts: The number of times a service is re-checked
    before changing into a hard state
    - check_period: he name of a time period which determines when
    this service should be checked
    - check_timeout: Check command timeout in seconds
    - check_interval: The check interval in seconds
    - retry_interval: The retry interval in seconds
    - enable_notifications: Whether notifications are enabled
    - enable_active_checks: Whether active checks are enabled
    - enable_passive_checks: Whether passive checks are enabled
    - enable_event_handler: Enables event handlers for this host
    - enable_flapping: Whether flap detection is enabled
    - flapping_threshold_high: Flapping upper bound in percent for a
    service to be considered flapping
    - flapping_threshold_low: Flapping lower bound in percent for a
    service to be considered not flapping.
    - enable_perfdata: Whether performance data processing is enabled
    - event_command: The name of an event command that should be executed
    every time the service’s state changes or the service is in a SOFT state
    - volatile: The volatile setting enables always HARD state types if NOT-OK
    state changes occur
    - zone: The zone this object is a member of
    - command_endpoint: The endpoint where commands are executed on
    - notes: Notes for the service
    - notes_url: URL for notes for the service
    - action_url: URL for actions for the service
    - icon_image: Icon image for the service
    - icon_image_alt: Icon image description for the service
    """
    conf = """
    object Service "{{ template.name }}" {
        host_name = "{{ data.hostname }}"
        {% if template.display_name is defined %}
        display_name = "{{ template.display_name }}"
        {% endif %}
        {% if template.groups in defined %}
        groups = [{% for group in template.groups %}"{{ group }}",{% endfor %}]
        {% endif %}
        {% if template.max_check_attempts is defined %}
        max_check_attempts = "{{ template.max_check_attempts }}"
        {% endif %}
        {% if template.check_command is defined %}
        check_command = "{{ template.check_command }}"
        {% endif %}
        {% if template.vars is defined %}
        {% for key, value in template.vars.items() %}
        vars.{{ key }} = "{{ value }}"
        {% endfor %}
        {% endif %}
        {% if template.check_period is defined %}
        check_period = "{{ template.check_period }}"
        {% endif %}
        {% if template.check_timeout is defined %}
        check_timeout = "{{ template.check_timeout }}"
        {% endif %}
        {% if template.check_interval is defined %}
        template.check_interval = "{{ template.check_interval }}"
        {% endif %}
        {% if template.retry_interval is defined %}
        retry_interval = "{{ template.retry_interval }}"
        {% endif %}
        {% if template.enable_notifications is defined %}
        enable_notifications = {{ template.enable_notifications|lower }}
        {% endif %}
        {% if template.enable_active_checks is defined %}
        enable_active_checks = {{ template.enable_active_checks|lower }}
        {% endif %}
        {% if template.enable_passive_checks is defined %}
        enable_passive_checks = {{ template.enable_passive_checks|lower }}
        {% endif %}
        {% if template.enable_event_handler is defined %}
        enable_event_handler = {{ template.enable_event_handler|lower }}
        {% endif %}
        {% if template.enable_flapping is defined %}
        enable_flapping = {{ template.enable_flapping|lower }}
        {% endif %}
        {% if template.enable_perfdata is defined %}
        enable_perfdata = {{ template.enable_perfdata|lower }}
        {% endif %}
        {% if template.event_command is defined %}
        event_command = "{{ template.event_command }}"
        {% endif %}
        {% if template.flapping_threshold is defined %}
        flapping_threshold = "{{ template.flapping_threshold }}"
        {% endif %}
        {% if template.flapping_threshold_high is defined %}
        flapping_threshold_high = {{ template.flapping_threshold_high }}
        {% endif %}
        {% if template.flapping_threshold_low is defined %}
        flapping_threshold_low = {{ template.flapping_threshold_low }}
        {% endif %}
        {% if template.volatile is defined %}
        volatile = "{{ template.volatile }}"
        {% endif %}
        {% if template.zone is defined %}
        zone = "{{ template.zone }}"
        {% endif %}
        {% if template.command_endpoint is defined %}
        command_endpoint = "{{ template.command_endpoint }}"
        {% endif %}
        {% if template.notes is defined %}
        notes = "{{ template.notes }}"
        {% endif %}
        {% if template.notes_url is defined %}
        notes_url = "{{ template.notes_url }}"
        {% endif %}
        {% if template.action_url is defined %}
        action_url = "{{ template.action_url }}"
        {% endif %}
        {% if template.icon_image is defined %}
        icon_image = "{{ template.icon_image }}"
        {% endif %}
        {% if template.icon_image_alt is defined %}
        icon_image_alt = "{{ template.icon_image_alt }}"
        {% endif %}
    }
    """
    return Environment(trim_blocks=True,
                       lstrip_blocks=True).from_string(conf).render(data=data,
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
            response = requests.get(str(url),
                                    auth=(str(user),
                                          str(password)),
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
        LOGGER.info(results)
        return results


def post_api_request(url,
                     user,
                     password,
                     data=None,
                     ssl_verify=False):
    '''
      Cretate (PUT) configuration files to Icinga2 master
    '''
    headers = {'Accept': 'application/json'}

    if url is None:
        LOGGER.error("FAIL: Icinga2 URL is missing")
    elif user is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    elif password is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    else:
        try:
            if data is None:
                response = requests.post(url,
                                         auth=(user, password),
                                         headers=headers,
                                         verify=ssl_verify)
            else:
                response = requests.post(url,
                                         auth=(user, password),
                                         headers=headers,
                                         data=data,
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
        LOGGER.info("URI: %s \n%s", url, response_data)


def delete_api_request(url,
                       user,
                       password,
                       ssl_verify=False):
    """
        Delete (DELETE) configuration files from Icinga2 master
    """
    if url is None:
        LOGGER.error("FAIL: Icinga2 URL is missing")
    elif user is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    elif password is None:
        LOGGER.error("FAIL: Icinga2 user is missing")
    else:
        try:
            response = requests.delete(str(url),
                                       auth=(str(user),
                                             str(password)),
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
        LOGGER.info(results)


def delete_monitoring(metadata,
                      api_endpoint,
                      api_port,
                      api_user,
                      api_pass):
    """
        Delete monitoring configuration from Icinga2 master
    """
    pkg_url = "https://{0}:{1}/v1/config/packages/{2}".format(api_endpoint,
                                                              api_port,
                                                              metadata['hostname'])
    delete_api_request(pkg_url,
                       api_user,
                       api_pass)
    LOGGER.info("Removed Icinga2 configuration for %s", metadata['hostname'])


def setup_monitoring(metadata,
                     template_bucket,
                     api_endpoint,
                     api_port,
                     api_user,
                     api_pass):
    """
        Setup monitoring for host in Icinga2 master by creating Icinga2
        package/stage files in Icinga2 master
        Parameters:
            - instance_id: ec2 instance ID
    """
    templates = {}
    templates['endpoint'] = "endpoint/{0}".format(metadata['l2i_endpoint_template'])
    templates['zone'] = "zone/{0}".format(metadata['l2i_zone_template'])
    templates['host'] = "host/{0}".format(metadata['l2i_host_template'])
    templates['service'] = "service/{0}".format(metadata['l2i_service_template'])

    # Retrieve endpoint configuration template
    endpoint_conf_tpl = get_conf_template(template_bucket,
                                          templates['endpoint'])
    # Retrieve zone configuration template
    zone_conf_tpl = get_conf_template(template_bucket,
                                      templates['zone'])
    # Retrieve host configuration template from template store (S3 bucket)
    host_conf_tpl = get_conf_template(template_bucket,
                                      templates['host'])
    # Retrieve service configuration template from template store (S3 bucket)
    service_conf_tpl = get_conf_template(template_bucket,
                                         templates['service'])
    LOGGER.info(yaml.load(host_conf_tpl))
    LOGGER.info(yaml.load(service_conf_tpl))
    # Step 1: Check if configuration package exist
    pkg_base_url = "https://{0}:{1}/v1/config/packages".format(api_endpoint,
                                                               api_port)
    packages = get_api_request(pkg_base_url, api_user, api_pass)
    pkg_uri = pkg_base_url + "/{0}".format(metadata['hostname'])
    stg_uri = "https://{0}:{1}/v1/config/stages/{2}".format(api_endpoint,
                                                            api_port,
                                                            metadata['hostname'])
    conf_exist = False
    # check if package for the host exist
    for package in packages:
        if package['name'] == metadata['hostname']:
            conf_exist = True
            break
    # if configuration package does not exist, create new one
    if not conf_exist:
        LOGGER.info('Creating pkg %s', metadata['hostname'])
        post_api_request(pkg_uri, api_user, api_pass)

    # Generate endpoint configuration
    content = generate_endpoint_configuration(metadata, yaml.load(endpoint_conf_tpl))
    # Generate zone configuration
    content += generate_zone_configuration(metadata, yaml.load(zone_conf_tpl))
    # Generate host configuration content
    content += generate_host_configuration(metadata, yaml.load(host_conf_tpl))
    # Generate service configuration content
    services = yaml.load(service_conf_tpl)
    for service in services:
        content += generate_service_configuration(metadata, service)
    LOGGER.info(content)
    # Create host configuration stage
    if content is not None:
        data = {}
        conf_path = 'conf.d/{0}.conf'.format(metadata['hostname'])
        data['files'] = {conf_path: content}
        post_api_request(stg_uri,
                         api_user,
                         api_pass,
                         json.dumps(data))
        LOGGER.info("Monitoring enabled for: %s", metadata['hostname'])


def downtime_check(url,
                   duration,
                   api_user,
                   api_pass,
                   comment):
    """
        Send request to downtime Icinga2 check
    """
    downtime_data = {}
    now = datetime.utcnow()
    downtime_data['start_time'] = calendar.timegm(now.utctimetuple())
    end_timestamp = datetime.utcnow() + timedelta(minutes=duration)
    downtime_data['end_time'] = calendar.timegm(end_timestamp.timetuple())
    downtime_data['author'] = 'automagic-lambda2icinga'
    downtime_data['comment'] = comment
    post_api_request(url,
                     api_user,
                     api_pass,
                     json.dumps(downtime_data))
    LOGGER.info("Check downtimed for: %s", url)


def handler(event, context):
    """
        AWS Lambda main method
    """
    try:
        template_bucket = environ['TEMPLATES_BUCKET']
    except KeyError:
        LOGGER.error('Please set the enviroment variable "TEMPLATES_BUCKET"')

    try:
        api_user = environ['API_USER']
    except KeyError:
        LOGGER.error('Please set the enviroment variable "API_USER"')

    try:
        api_pass = environ['API_PASS']
    except KeyError:
        LOGGER.error('Please set the enviroment variable "API_PASS"')

    try:
        api_port = environ['API_PORT']
    except KeyError:
        LOGGER.warning('"API_PORT" value is missing. Using default: \'5665\'')
        api_port = 5665

    try:
        api_endpoint = environ['API_ENDPOINT']
    except KeyError:
        LOGGER.error('Please set the enviroment variable "API_ENDPOINT"')

    LOGGER.info("Event: \n" + str(event))
    LOGGER.info("Context: \n" + str(context))
    if event['source'] == 'aws.ec2':
        if event['detail-type'] == 'EC2 Instance State-change Notification':
            instance_id = event['detail']['instance-id']
            if event['detail']['state'] == 'running':
                ec2_filters = [{
                    "Name": "tag:lambda2icinga",
                    "Values": ["enabled", "True", "true"]
                }, {
                    "Name": "instance-id",
                    "Values": [instance_id]}]
                data = get_instance_data(ec2_filters)
                for metadata in data:
                    setup_monitoring(metadata,
                                     template_bucket,
                                     api_endpoint,
                                     api_port,
                                     api_user,
                                     api_pass)
            elif event['detail']['state'] == 'terminated':
                ec2_filters = [{
                    "Name": "instance-id",
                    "Values": [instance_id]
                }]
                data = get_instance_data(ec2_filters)
                for metadata in data:
                    delete_monitoring(metadata,
                                      api_endpoint,
                                      api_port,
                                      api_user,
                                      api_pass)
        elif event['detail-type'] == 'AWS API Call via CloudTrail':
            event_name = event['detail']['eventName']
            instance_id = event['detail']['requestParameters']['resourcesSet']['items'][0]['resourceId']
            tags = event['detail']['requestParameters']['tagSet']['items']
            if event_name == 'CreateTags':
                for tag in tags:
                    if tag['key'] in ['lambda2icinga',
                                      'l2i_host_template',
                                      'l2i_service_template',
                                      'l2i_endpoint_template',
                                      'l2i_zone_template']:
                        ec2_filters = [{
                            "Name": "tag:lambda2icinga",
                            "Values": ["enabled", "True", "true"]
                        }]
                        data = get_instance_data(ec2_filters)
                        for metadata in data:
                            setup_monitoring(metadata,
                                             template_bucket,
                                             api_endpoint,
                                             api_port,
                                             api_user,
                                             api_pass)
                            # Downtime just created host check
                            downtime_url = "https://{0}:{1}/v1/actions/schedule-downtime?type=Host&filter=host.name==\"{2}\"".format(api_endpoint,
                                                                                                                                     api_port,
                                                                                                                                     metadata['hostname'])
                            downtime_check(downtime_url,
                                           api_user,
                                           api_pass,
                                           'New host 15 min auto-downtime')

                        break
            elif event_name == 'DeleteTags':
                if event['detail']['requestParameters']['tagSet']['items'][0]['key'] == 'lambda2icinga':
                    ec2_filters = [{
                        "Name": "instance-id",
                        "Values": [instance_id]
                    }]
                    data = get_instance_data(ec2_filters)
                    for metadata in data:
                        delete_monitoring(metadata,
                                          api_endpoint,
                                          api_port,
                                          api_user,
                                          api_pass)
                else:
                    for tag in tags:
                        if tag['key'] in ['l2i_host_template',
                                          'l2i_service_template',
                                          'l2i_endpoint_template',
                                          'l2i_zone_template']:
                            ec2_filter = [{
                                "Name": "instance-id",
                                "Values": [instance_id]
                            }]
                            data = get_instance_data(ec2_filters)
                            for metadata in data:
                                setup_monitoring(metadata,
                                                 template_bucket,
                                                 api_endpoint,
                                                 api_port,
                                                 api_user,
                                                 api_pass)
    elif event['Record'][0]['eventSource'] == 'aws.s3':
        object_key = event['Record'][0]['s3']['object']['key']
        template_name = object_key.split('/')[-1:]
        ec2_filters = {}
        if 'host' in object_key:
            ec2_filter['tag:l2i_host_template'] = template_name
        elif 'service' in object_key:
            ec2_filter['tag:l2i_service_template'] = template_name
        elif 'endpoint' in object_key:
            ec2_filter['tag:l2i_endpoint_template'] = template_name
        elif 'zone' in object_key:
            ec2_filter['tag:l2i_zone_template'] = template_name
        data = get_instance_data(ec2_filters)
        for metadata in data:
            setup_monitoring(metadata,
                             template_bucket,
                             api_endpoint,
                             api_port,
                             api_user,
                             api_pass)
