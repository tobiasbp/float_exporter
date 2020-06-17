# float_exporter
An exporter for Prometheus exposing data from project management service Float at float.com

When running on *localhost*, *float_exporter* expose metrics at `http://localhost:9709/metrics`

# Metrics
The metrics exposed by *float_exporter*.

* ?
* ?

# Configuration
How to configure *float_exporter*.

## Parameters
The following parameters make up the configuration of *float_exporter*.

* *email*: An email where you can be contacted. Required by Float.
* *user_agent*: A string to use as User-Agent along with your contact email. Required by Float.
* *log_file*: The path to the configuration file you want to use.
* *log_level*: The level of logging
* *access_token*: The Float access token to use (Get in _settings/integration_ in GUI)
* *port*: The port to accept traffic on. Default is 9709.
* *report_days*: A list of days in the future to create reports for.



## Priority
*float_exporter* has three sources of configuration. They are the following, in order of priority.
1 Arguments supplied via flags when running *float_exporter*
2 Environment variables
3 Configuration file

When setting a parameter using an environment variable, you should prefix the
parameter name in uppercase with the string *FLOAT_*. To set the access token to use
you would need to specify the environment variable *FLOAT_ACCESS_TOKEN*.

# Run in Kubernetes
Run *float_exporter* as a servive in a Kubernetes cluster managed by *kubectl*.
This section refers to files in directory *k8s*.
All files uses namespace *automation*. If you want to use a different namespace,
you can change the configuration files accordingly.

* Clone repository
* Add namespace *automation*: `kubectl create -f namespace.yml`
* Copy *fe-secret.yml* to *fe-secret.local.yml* and add your Float access token
* Create secret in Kubernetes: `kubectl create -f fe-secret.local.yml`
* Copy *fe-configmap.yml* to *fe-configmap.local.yml* and change to you liking. You must add a valid email.
* Create configmap in Kubernetes: `kubectl create -f fe-configmap.local.yml`
* Create the *fe-svc* service and *fe-dep* deployment in Kubernetes: `kubectl create -f fe-service.yml`


# Run locally

* Clone repository
* Install Python packages: `pip3 install -r requirements.txt`
* Copy config file *float_exporter.yml* to *float_exporter.local.yml*
* Update *float_exporter.local.yml* with your configuration.
* Run float_exporter.py: `./float_exporter.py ./float_exporter.local.yml`

# Run in Docker

## Build image
Build an image with tag *float_exporter*.
* Clone repository
* Build the image: `docker build --tag float_exporter .`

## Configuration in file
How to run with configuration in a file.
* Copy *float_exporter.yml* to */example/path/float_exporter.yml* (An example path).
* Update */example/path/float_exporter.yml* with your configuration.
* Run the container: `docker run --rm -p 9709:9709 -v /example/path/float_exporter.yml:/etc/float_exporter.yml float_exporter`
* You should see the log from float_exporter confirming a successful run.

## Configuration with environment variables
If you don't want to map an external config file to the container, you can pass
environment variables for the container to use in stead of the values in the configuration
file */etc/float_config.yml*. Here is an example of setting
the access token to be used by *float_exporter*.

* `docker run --rm --env FLOAT_ACCESS_TOKEN=****** -p 9709:9709 float_exporter`

You should probably always use the flag *--rm* to remove the container when stopping float_exporter.
If you don't do that, you will end up with a lot of unused containers. If you want to keep the log file,
you should map an external directory to */var/log* in the container as a *volume*.

