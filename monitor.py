import threading
import yaml
import requests
import time
from collections import defaultdict
import logging
import datetime


LOGGING_LEVEL = 'INFO'
MONITORING = True
DEFAULT_TIMEOUT = 5
DEFAULT_REQUEST_INTERVAL= 5
DEFAULT_REPORTING_INTERVAL = 15
domain_stats = defaultdict(lambda: {"up": 0, "total": 0})


# Returns formatted timestamp in local time
def get_timestamp():
    return datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S -')



def load_config(file_path):
    """Function to load configuration from the YAML file. 
    If the file passed does not contain valid YAML, print an error message and return None. 
    Otherwise, check all required fields are present in each endpoint and return the config.
    
    Keyword arguments:
    file_path -- path to the YAML file
    """
    with open(file_path, 'r') as file:
        try:
            config = yaml.safe_load(file) 
            for endpoint in config:
                if 'name' not in endpoint:
                    logging.error(f"Endpoint missing 'name': {endpoint}")
                    return None
                if 'url' not in endpoint:
                    logging.error(f"Endpoint missing 'url': {endpoint}")
                    return None
            return config
        except yaml.YAMLError as e:
            print(f"Invalid YAML: {e}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None


def increment_stats(domain, result):
    """ 
    Function to increment the stats for a domain. Implements thread safety.
    Keyword arguments:
    domain -- domain name
    """
    logging.debug(f"{get_timestamp()} {domain} is {result}")

    with threading.Lock():
        domain_stats[domain]["total"] += 1
        if result == "UP":
            domain_stats[domain]["up"] += 1
            logging.debug(f"{get_timestamp()} {domain} is {result}")



def send_request(endpoint): 
    """
    This is the main method for the 'request' thread. 
    It sends a request to the endpoint and determine its status.
    Calls increment_stats to report the status.
    HTML Request fields are set based on values in the endpoint dictionary.

    Endpoint is considered "UP" if the response code is between 200 and 299
    and response time is less than the timeout (default 500ms), otherwise "DOWN".


    Keyword arguments:
    endpoint -- dictionary containing endpoint information
    """
    domain = endpoint["url"].split("//")[-1].split("/")[0]
    url = endpoint['url']
    method = endpoint.get('method', 'GET')
    headers = endpoint.get('headers')
    body = endpoint.get('body')
    timeout = endpoint.get('timeout', DEFAULT_TIMEOUT)

    try:
        logging.info(f"{get_timestamp()} Checking {endpoint} ...")

        response = requests.request(method, url, headers=headers, json=body, timeout=timeout)
        logging.debug(f"{get_timestamp()} Response from {endpoint} is {response}")
        
        if 200 <= response.status_code < 300:
            result = "UP"
        else:
            result = "DOWN"
    except requests.RequestException:
        result = "DOWN"
    
    increment_stats(domain, result)


def check_health(endpoint):
    """
    This is the main method for the 'looping' thread.
    It starts a new 'request' thread for each endpoint, sleeps for the interval.

    Interval is set based on values in the endpoint dictionary, and defaults to DEFAULT_REQUEST_INTERVAL.

    Warning is issued if request interval is less than timeout for that endpoint or
    the request thread still alive after the sleeping interval.

    Keyword arguments:
    endpoint -- dictionary containing endpoint information
    """
    interval = endpoint.get('interval', DEFAULT_REQUEST_INTERVAL)
    timeout = endpoint.get('timeout', DEFAULT_TIMEOUT)

    while MONITORING:

        if interval < timeout:
            logging.warning(f"{get_timestamp()} Interval is less than timeout for {endpoint['url']}, which can cause serious performance issues")

        request_thread = threading.Thread(target=send_request, args=(endpoint,))
        request_thread.start()
        time.sleep(interval)

        if request_thread.is_alive():
            logging.warning(f"{get_timestamp()} Request to {endpoint['url']} is still alive")

        
def monitor_endpoints(config):
    """
    Function to monitor endpoints. It starts one 'looping' thread for each endpoint.
    Keyword arguments:
    config -- list of dictionaries containing endpoint information
    """

    for endpoint in config:
        endpoint_thread = threading.Thread(target=check_health, args=(endpoint,))
        endpoint_thread.start()


def print_availability():
    """
    Function to print availability percentages for each domain. It is the working function 
    of the 'reporting' thread.

    It sleeps for the reporting interval and prints the availability percentages for each domain.

    """
    while MONITORING:
        if domain_stats:
            for domain, stats in domain_stats.items():

                availability = round(100 * stats["up"] / stats["total"])
                print(f"{get_timestamp()} {domain} has {availability}% availability percentage")
        else:
            print("No endpoints monitored yet.")

        print("---")
        time.sleep(DEFAULT_REPORTING_INTERVAL)
  

# Entry point of the program
if __name__ == "__main__":
    """
    Main function to start the monitoring process.
    It loads the configuration from the YAML file, starts the 'reporting' thread and
    calls monitor_endpoints() to start the 'looping' thread for each endpoint.
    """

    import sys

    logging.basicConfig(level=LOGGING_LEVEL)

    if len(sys.argv) != 2:
        logging.error("Usage: python monitor.py <config_file_path>")
        sys.exit(1)

    config_file = sys.argv[1]
    config = load_config(config_file)

    if config:
        try:
            printing_thread = threading.Thread(target=print_availability)
            printing_thread.start()
            monitor_endpoints(config)
        except KeyboardInterrupt:
            MONITORING = False
            logging.warning("Monitoring stopped by user.")

        

