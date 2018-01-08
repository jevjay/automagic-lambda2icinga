"""

"""
from os import environ
import sys
import json
import logging
from datetime import datetime, timedelta
import calendar
import requests

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


def create_package(package_name,
                   api_endpoint,
                   api_port,
                   api_user,
                   api_pass):
    """

    """
    url = "https://{0}:{1}/v1/config/packages".format(api_endpoint,
                                                      api_port)
    # Get all available packages
    packages = get_api_request(url, api_user, api_pass)
    # Set flag for package existance
    exist = False
     # check if package for the host exist
    for package in packages:
        if package['name'] == package_name:
            exist = True
            break

    if not exist:
        LOGGER.info('Creating pkg %s', package_name)
        pkg_url = url + "/{0}".format(package_name)
        post_api_request(pkg_url, api_user, api_pass)


def delete_package(package_name,
                   api_endpoint,
                   api_port,
                   api_user,
                   api_pass):
    """

    """
    url = "https://{0}:{1}/v1/config/packages/{2}".format(api_endpoint,
                                                          api_port,
                                                          package_name)
    delete_api_request(url,
                       api_user,
                       api_pass)


def create_stage(package_name,
                 objects,
                 api_endpoint,
                 api_port,
                 api_user,
                 api_pass):
    """

    """
    url = "https://{0}:{1}/v1/config/stages/{2}".format(api_endpoint,
                                                        api_port,
                                                        package_name)
    payload = {}
    conf = {}

    for obj in objects:
        conf[obj['path']] = obj['content']

    payload['files'] = conf

    post_api_request(url,
                     api_user,
                     api_pass,
                     json.dumps(payload))


def update_monitoring(data,
                      api_endpoint,
                      api_port,
                      api_user,
                      api_pass):
    """

    """
    # First create package for the monitoring
    create_package(data['pkg_name'],
                   api_endpoint,
                   api_port,
                   api_user,
                   api_pass)
    # Create stage for specified package
    create_stage(data['pkg_name'],
                 data['objects'],
                 api_endpoint,
                 api_port,
                 api_user,
                 api_pass)


def delete_monitoring(data,
                      api_endpoint,
                      api_port,
                      api_user,
                      api_pass):
    """

    """
    delete_package(data['pkg_name'],
                   api_endpoint,
                   api_port,
                   api_user,
                   api_pass)
    LOGGER.info("Removed Icinga2 configuration for %s", data['pkg_name'])


def downtime_check(api_endpoint,
                   api_port,
                   api_user,
                   api_pass,
                   duration,
                   comment):
    """
        Send request to downtime Icinga2 check
    """
    url = "https://{0}:{1}//v1/actions/schedule-downtime".format(api_endpoint,
                                                                 api_port)
    downtime_data = {}
    now = datetime.utcnow()
    downtime_data['start_time'] = calendar.timegm(now.utctimetuple())
    end_timestamp = datetime.utcnow() + timedelta(minutes=duration)
    downtime_data['end_time'] = calendar.timegm(end_timestamp.timetuple())
    downtime_data['author'] = 'lambda2icinga'
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
    # Get environment variables
    api_endpoint = env_var('API_ENDPOINT')
    api_port = env_var('API_PORT')
    api_user = env_var('API_USER')
    api_pass = env_var('API_PASS')

    if event['type'] == 'update_monitoring':
        update_monitoring(event,
                          api_endpoint,
                          api_port,
                          api_user,
                          api_pass)
    elif event['type'] == 'delete_monitoring':
        delete_monitoring(event,
                          api_endpoint,
                          api_port,
                          api_user,
                          api_pass)
