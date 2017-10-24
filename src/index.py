"""

"""
from os import environ
from sys import exit
from string import Template
import logging
import boto3
from botocore.errorfactory import ClientError
import json
import yaml
from jinja2 import Environment

# Configure LOGGER object
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


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
            exit(1)


def generate_zone_configuration(zones):
    """
    Generates Icinga2 zone configuration file from the template
    Zone object params:
    - endpoints: Array of endpoint names located in this zone
    - parent: The name of the parent zone
    - global: flag to sync confgiuration files across all nodes within zone
    """
    TEMPLATE = """
    {% for zone in zones %}
    object Zone "{{ zone.name }}" {
        endpoints = [ {{ zone.name }} ]
        {% if zone.parent is not None %}
        parent = {{ zone.parent }}
        {% endif %}
        {% if zone.global %}
        global = "true"
        {% endif %}
    }\n
    {% endfor %}
    """
    return Environment().from_string(TEMPLATE).render(zones=zones)


def generate_endpoint_configuration(endpoints):
    """
    Generates Icinga2 endpoing configuration file from the template
    Endpoint object params:
    - host: The hostname/IP address of the remote Icinga 2 instance.
    - port: The service name/port of the remote Icinga 2 instance.
    - log_duration: Duration for keeping replay logs on connection loss.
    """
    TEMPLATE = """
    {% for endpoint in endpoints %}
    object Endpoint "{{ endpoint.name }}" {
        {% if endpoint.host is not None %}
        host = {{ endpoint.host }}
        {% endif %}
        {% if endpoint.port is not None %}
        port = {{ endpoint.port }}
        {% endif %}
        {% if endpoint.log_duration is not None %}
        log_duration = {{ endpoint.log_duration }}
        {% endif %}
    }\n
    {% endfor %}
    """
    return Environment().from_string(TEMPLATE).render(endpoints=endpoints)


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
    TEMPLATE = """
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
        groups = [{% for group in template.groups %}"{{group}}",{% endfor %}]
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

    return Environment().from_string(TEMPLATE).render(data=data,
                                                      template=template)


def generate_service_configuration(data, template=None):
    """

    """
    config = []
    # Required parameters
    config.append("\thost_name = \"{0}\"".format(data['PrivateDnsName']))
    # Optional parameters
    if template['display_name'] is not None:
        config.append("\tdisplay_name = \"{0}\"".format(template['display_name']))

    if template['groups'] is not None:
        config.append("\tgroups = \"{0}\"".format(template['groups']))

    if template['max_check_attempts'] is not None:
        config.append("\tmax_check_attempts = \"{0}\"".format(template['max_check_attempts']))

    if template['check_period'] is not None:
        config.append("\tcheck_period = \"{0}\"".format(template['check_period']))

    if template['check_timeout'] is not None:
        config.append("\tcheck_timeout = \"{0}\"".format(template['check_timeout']))

    if template['check_interval'] is not None:
        config.append("\tcheck_interval = \"{0}\"".format(template['check_interval']))

    if template['retry_interval'] is not None:
        config.append("\tretry_interval = \"{0}\"".format(template['retry_interval']))

    if template['enable_notifications'] is not None:
        config.append("\tenable_notifications = \"{0}\"".format(template['enable_notifications']))

    if template['enable_active_checks'] is not None:
        config.append("\tenable_active_checks = \"{0}\"".format(template['enable_active_checks']))

    if template['enable_passive_checks'] is not None:
        config.append("\tenable_passive_checks = \"{0}\"".format(template['enable_passive_checks']))

    if template['enable_event_handler'] is not None:
        config.append("\tenable_event_handler = \"{0}\"".format(template['enable_event_handler']))

    if template['enable_flapping'] is not None:
        config.append("\tenable_flapping = \"{0}\"".format(template['enable_flapping']))

    if template['enable_perfdata'] is not None:
        config.append("\tenable_perfdata = \"{0}\"".format(template['enable_perfdata']))

    if template['event_command'] is not None:
        config.append("\tevent_command = \"{0}\"".format(template['event_command']))

    if template['flapping_threshold'] is not None:
        config.append("\tflapping_threshold = \"{0}\"".format(template['flapping_threshold']))

    if template['volatile'] is not None:
        config.append("\tvolatile = \"{0}\"".format(template['volatile']))

    if template['zone'] is not None:
        config.append("\tzone = \"{0}\"".format(template['zone']))

    if template['command_endpoint'] is not None:
        config.append("\tcommand_endpoint = \"{0}\"".format(template['command_endpoint']))

    if template['notes'] is not None:
        config.append("\tnotes = \"{0}\"".format(template['notes']))

    if template['notes_url'] is not None:
        config.append("\tnotes_url = \"{0}\"".format(template['notes_url']))

    if template['action_url'] is not None:
        config.append("\taction_url = \"{0}\"".format(template['action_url']))

    if template['icon_image'] is not None:
        config.append("\ticon_image = \"{0}\"".format(template['icon_image']))
    # SOME VARIABLES ARE MISSING
    if template['icon_image_alt'] is not None:
        config.append("\ticon_image_alt = \"{0}\"".format(template['icon_image_alt']))

    content = Template("object Service $servicename {\n" +
                       "$config\n" +
                       "}")
    result = content.safe_substitute(servicename='test',
                                     config='\n'.join(config))
    return json.dump(result)


def conf_object_exist(url,
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


def create_conf_object(url,
                       user,
                       password,
                       data,
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
            response = requests.put(url,
                                    auth=(user, password),
                                    data=data,
                                    headers=headers,
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


def update_conf_object(url,
                       user,
                       password,
                       data,
                       ssl_verify=False):
    '''
      Update (POST) configuration files for Icinga2 master
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
            response = requests.post(url,
                                     auth=(user, password),
                                     data=data,
                                     headers=headers,
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
    metadata = event['Records'][0]
    template_bucket = environ['TEMPLATES_BUCKET']
    api_user = environ['API_USER']
    api_pass = environ['API_PASS']
    api_port = environ['API_PORT']
    api_endpoint = environ['API_ENDPOINT']

    templates = {}
    templates['host'] = "host/{0}".format(metadata['host_template'])
    templates['endpoint'] = "endpoint/{0}".format(metadata['endpoint_template'])
    templates['zone'] = "zone/{0}".format(metadata['endpoint_template'])
    templates['service'] = "service/{0}".format(metadata['service_template'])

    # Retrieve host configuration template from template store (S3 bucket)
    host_conf_tpl = get_conf_template(template_bucket,
                                      templates['host'])
    # Retrieve endpoint configuration template from template store (S3 bucket)
    endpnt_conf_tpl = get_conf_template(template_bucket,
                                        templates['endpoint'])
    # Retrieve zone configuration template from template store (S3 bucket)
    zone_conf_tpl = get_conf_template(template_bucket,
                                      templates['zone'])
    # Retrieve service configuration template from template store (S3 bucket)
    service_conf_tpl = get_conf_template(template_bucket,
                                         templates['service'])
    # Generate hody configuration content
    #generate_host_configuration(metadata, yaml.load(host_conf_tpl))
    # Generate zone configuration content
    #generate_zone_configuration(metadata, yaml.load(zone_conf_tpl))
    # Generate service configuration content
    #generate_service_configuration(metadata, yaml.load(service_conf_tpl))
    # GENERATE CLIENT ZONE CONFIGURATION
