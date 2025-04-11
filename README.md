# HTTP Response Monitor

## Overview 

This repository contains two monitoring scripts, several example input files, and a handful of unit tests. Both scripts accomplish the same goal; monitor the responses from the endpoints specified in the config file. Requests are sent and cumulative availability is reported every 15s by default. 

The `main.py` script is a more direct solution while still fitting each requirement, while the `monitor.py` script contains additional changes. 

These changes include:
- Support for additional optional parameters in the config file
- Implementing logging framework (increases readability during development and debugging)
- Timestamps in reporting messages
- More robust input validation


## Install & Run

1. Clone Repository 

    ```
    git clone https://github.com/rkfergus/th-fetch.git
    cd th-fetch
    ```

2. Create Virtual Environment & Download Dependencies 

    ```
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3. Run the monitoring script and specify the config file. 

    ```
    python monitor.py <path-to-config>
    # Example
    python monitor.py ex-configs/generic_sample.yaml
    ```

## Issues Identified 

1. Run time error occurs when no method is specified in the input yaml file. 

    - **Error Message**: 

        ```Traceback (most recent call last):
        File "/Users/keli/repos/fetch-take-home/sre-take-home-exercise-python/main.py", line 59, in <module>
            monitor_endpoints(config_file)
            ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
        File "/Users/keli/repos/fetch-take-home/sre-take-home-exercise-python/main.py", line 35, in monitor_endpoints
            result = check_health(endpoint)
        File "/Users/keli/repos/fetch-take-home/sre-take-home-exercise-python/main.py", line 19, in check_health
            response = requests.request(method, url, headers=headers, json=body)
        File "/Users/keli/repos/fetch-take-home/sre-take-home-exercise-python/.venv/lib/python3.13/site-packages/requests/api.py", line 59, in request
            return session.request(method=method, url=url, **kwargs)
                ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/Users/keli/repos/fetch-take-home/sre-take-home-exercise-python/.venv/lib/python3.13/site-packages/requests/sessions.py", line 564, in request
            method=method.upper(),
                ^^^^^^^^^^^^
        AttributeError: 'NoneType' object has no attribute 'upper'```

    - **Cause**: In the `check_health()` method, the 'method' variable is None when the HTTP method is not specified in the input yaml file. This variable is passed as a parameter to `requests.request()`. Method is a required parameter, so an error is thrown when the monitoring script calls that function with the value None for method. 
    - **Resolution**: Per specifications, the default HTTP method is GET. In order to resolve the error and adhere to our requirements, the 'method' variable in the `check_health()` needs to default to GET if one is not specified in the yaml file. 
2. Ports on the same domain handled indepentdently 
    - **Problem**: When parsing the domain from the URL, port number is still included. As is "example.org" and "example.org:443" are reported as separate domains and their availability is calculated independently. 
    - **Resolution**: Add an additional `.split()` to the line where parsing occurs, splitting on ":" and returning only the first value. 
3. Request method not called with a timeout value
    - **Problem**: The requirements state that a response time of more than 500ms is considered DOWN, whether the eventual response is valid or not. As written, the monitoring script will wait indefinitely for a request to respond and only accounts for response code. 
    - **Cause**: No timeout parameter set in `requests.request()` method call 
    - **Resolution**: 
        - Created a global variable `DEFAULT_TIMEOUT`, which will be passed to the `request()` function as a parameter. The parameter uses seconds, so it is set to 5. If a request is timed out, a Timeout exception is raised. Timeout exceptions (and all other exceptions raised by the Request library) are `RequestExceptions`, so we only need to add the parameter in order for timed out requests to be marked 'DOWN'.  
4. Availability is not logged every 15s. 
    - **Problem**: The original method of sleeping for 15s after every iteration through the endpoint array does not meet the requirement to log availability every 15s. 
    - **Cause**: Under this implementation, the reporting interval is dependent on the combined response times of each endpoint. This is not particularly noticeable under normal operation with only a few endpoints, but will cause severe montioring issues if there is a spike in response time on any endpoint, even if it is still eventually returning a valid response. Under the current implemetation, the monitoring script runs the risk of getting stuck on one endpoint if any of them are timing out. This is especially dangerous if the endpoints being monitored don't have robust error handling on their own. Each of these issues become a bigger problem as more endpoints are added to the config file. 
    - **Resolution**: The immediate problem is that the timer on calculating and printing the availability is happening on the same thread as the requests. The calculating and printing needs moved to it's own function, with it's own sleep timer, and ran in a separate thread. In order to do this, the `domain_stats` dictionary will need to be accessible by both the print and monitor functions. We can do this easily with a global variable. 
5. Moving the sleep timer to a separate thread doesn't solve all of timing problems, and introduces one of its own. 
    - **Problem**: With the sleep timer now on the new thread, there are two issues. First, if there are a larger number of endpoints being monitored, each endpoint may not be queried frequently enough for accurate availability numbers because they are being tested in sequence. A response time spike on one endpoint would also impact the monitoring of other endpoints. The other issue is that without any timer on the loop sending requests, it is possible to overload application servers depending on the normal/expected traffic that the API is designed for. For large scale applications the request count from monitoring may not make a meaningful difference, but it could be detrimental to smaller scale applications. 
    - **Cause**: There is no frequency limit set on requests to the application. 
    - **Resolution**: Set a frequency limit on the requests. We could add a sleep to the entire loop, but that would not fix the problems that arise from a large list of endpoints or high response times. If each endpoint is queried with it's own timer, that would solve both problems in most applications. 
        - There are a couple ways to accomplish this. The method I went with is slightly more complex but keeps the monitoring intveral consisent between loops, and keeps issues in one endpoint from affecting others. For each endpoint in the config, there is a 'looping' thread and a 'request' thread. This 'looping' thread starts a 'request' thread. The 'request' thread which sends the request and reports the response. The 'looping thread' sleeps for the alloted amount of time (which is configurable per endpoint) before starting a new thread. 
        - With the sleep happening on a separate thread than the request, the response time of the request will not affect the frequency of the request. While we have added a timeout to the request (discussed above), even a 500ms delay can compound over time. 
        - This approach now has mutliple threads writing to the same variable (`domain_stats`). In order to prevent any collision, a thread lock as been implemented on the write function to this variable. I also moved the write operations to a new function for readability. 
        - Due to the timeout on the request, the request thread should always finish before the sleep interval in the looping thread. Still, starting too many threads can cause performance issues so an error message was added in the looping thread to notify you if the previous thread for that endpoint is still alive when a new thread is about to be created. 

## Other Code Changes 

1. Input validation for yaml config file. 
    - The `load_config()` function now validates the yaml file. It checks if the file is valid YAML, is not empty, and contains the required parameters (name and url). 
2. Implemented logging framework. 
    - Converted all but main availability print statements to logging statements. Setting `LOGGING_LEVEL` to 'INFO' will be helpful for future developement, and can be set to 'DEBUG' if needed. 'WARNING' is recommended lowest setting, but 'ERROR' is acceptable. 
3. Added the following global variables: 
    - `MONITORING` - This flag is intially set to True, and set to false in the event of a keyboard interrupt. This allows the reporting loop to terminate on it's own, though it will finish its current loop unless there is an additional keyboard interrupt. 
    - `LOGGING_LEVEL` - Sets the logging level discussed above. 
    - `DEFAULT_INTERVAL` - Dictates how often a new request thread is started for each endpoint, unless another interval is set in the input file. Currently set to 15s, an assumption based on other requirements.
    - `DEFAULT_TIMEOUT` - Used as the timeout parameter for the HTTP request unless another timeout value is set in the input file. Currently set to 5s (500ms), per requirements. 
4. Added `get_timestamp()` method. 
    - This method is used to increase readability of logging statements. It uses the local time for the machine, but this can be changed by passing the 'tz' parameter to the datetime.now() function. 
    - Timestamps were added to logging statements to ensure accurate timing in both reporting and request loops. 






