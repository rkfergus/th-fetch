import threading
import yaml
import requests
import time
from collections import defaultdict


MONITORING = True
DEFAULT_INTERVAL= 15
DEFAULT_TIMEOUT = 5
domain_stats = defaultdict(lambda: {"up": 0, "total": 0})

# Function to load configuration from the YAML file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def increment_stats(domain, result):
    with threading.Lock():
        domain_stats[domain]["total"] += 1
        if result == "UP":
            domain_stats[domain]["up"] += 1



def send_request(endpoint): 
    domain = endpoint["url"].split("//")[-1].split("/")[0].split(":")[0]
    url = endpoint['url']
    method = endpoint.get('method', 'GET')
    headers = endpoint.get('headers')
    body = endpoint.get('body')

    try:
        response = requests.request(method, url, headers=headers, json=body, timeout=DEFAULT_TIMEOUT)

        if 200 <= response.status_code < 300:
            result = "UP"
        else:
            result = "DOWN"
    except requests.RequestException:
        result = "DOWN"
    
    increment_stats(domain, result)

# Function to perform health checks
def check_health(endpoint):

    while MONITORING:

        if DEFAULT_TIMEOUT > DEFAULT_INTERVAL:
            print(f"Interval is less than timeout for {endpoint['url']}, which can cause serious performance issues")

        request_thread = threading.Thread(target=send_request, args=(endpoint,))
        request_thread.start()
        time.sleep(DEFAULT_TIMEOUT)

        if request_thread.is_alive():
            print(f" Request to {endpoint['url']} is still alive")

        
# Main function to monitor endpoints, starts threads for each endpoint
def monitor_endpoints(file_path):
    config = load_config(file_path)
    for endpoint in config:
        threading.Thread(target=check_health, args=(endpoint,)).start()


# Log cumulative availability percentages
def print_availability():
    while MONITORING:
        if domain_stats:
            for domain, stats in domain_stats.items():

                availability = round(100 * stats["up"] / stats["total"])
                print(f"{domain} has {availability}% availability percentage")
        else:
            print("No endpoints monitored yet.")

        print("---")
        time.sleep(DEFAULT_INTERVAL)
  

# Entry point of the program
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python monitor.py <config_file_path>")
        sys.exit(1)

    config_file = sys.argv[1]
    try:
        printing_thread = threading.Thread(target=print_availability)
        printing_thread.start()
        monitor_endpoints(config_file)
    except KeyboardInterrupt:
        MONITORING = False
        print("\nMonitoring stopped by user.")

        

