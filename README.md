# Install

# Run 

# Issues Identified 
1. Run time error occurs when no method is specified in the input yaml file. 
    - Error Message: 
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

    - Cause: In the check_health() method, the 'method' variable is None when the HTTP method is not specified in the input yaml file. This variable is passed as a parameter to requests.request(). Method is a required parameter, so an error is thrown when the monitoring script calls that function with the value None for method. 
    - Resolution: Per specifications, the default HTTP method is GET. In order to resolve the error and adhere to our requirements, the 'method' variable in the check_health() needs to default to GET if one is not specified in the yaml file. 
    -