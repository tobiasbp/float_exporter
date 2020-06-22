# float_exporter
An exporter for Prometheus exposing data from project management service Float at float.com

When running on *localhost*, *float_exporter* expose metrics at `http://localhost:9709/metrics`

# Metrics
The metrics exposed by *float_exporter*. The label _days_, is the number of days beeing looked
in to the future when generating a report. A metric with _days="7"_ would cover the period
from the time the data was scraped, to _days_ days in the future. 

* float_accounts{account_type="['account_owner'|'admin'|'billing'|'member'|'project_manager']"}
* float_clients{}: Total number of clients.
* float_department_id{name="string"}: Mapping of department name to departmen_id.
* float_department_members{department_id="int"}: Number of people in department FIXME: Add department_id to people
* float_people{people_type=[1|2|3]}: Total number of people
* float_people_report_billable_hours{days="int",department_id="int"} Number of billable hours.
* float_people_report_capacity_hours{days="int",department_id="int"} Number of work hours available.
* float_people_report_nonbillable_hours{days="int",department_id="int"} Number of non billable hours.
* float_people_report_overtime_hours{days="int",department_id="int"} Number of overtime hours.
* float_people_report_scheduled_hours{days="int",department_id="int"} Number of scheduled hours.
* float_people_report_timeoff_hours{days="int",department_id="int"} Number of timeoff hours.
* float_people_report_unscheduled_hours{days="int",department_id="int"} Number of unscheduled hours.
* float_project_report_clients{days="int"} Number of clients worked for
* float_project_report_projects{days="int"} Number of projects worked on
* float_projects{active="[0|1]"} Total number of projects
* float_projects_billable{active="[0|1]"} Total number of billable projects 
* float_projects_budget_sum{type"=[1|2|3]"} Sum of project budgets
* float_projects_with_budget{type"=[1|2|3]"} Number of projects with a budget
* float_tasks{days="int",priority="[0|1]",status="['complete'|'confirmed'|'tentative']} Number of tasks.
* float_tasks_hours{days="int"} Number of task hours. 
* float_tasks_people{days="int"} Number of people with assigned tasks. 
* float_up{} Is data beeing pulled from Float? 0 = no, 1 = yes.
* float_accounts{priority="[0|1]",status=['complete'|'confirmed'|'tentative']}

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

# Run in Kubernetes with helm
Install *float_exporter* in a Kubernetes cluster from a helm chart. You are assumed to have helm
running on your machine. The following will install in namespace *default*.

* Clone repository
* Go to dir: `cd helm`
* Copy *config.yaml* to *config.local.yaml*
* Update *config.local.yaml* with your configuration
* Install: `helm install -f config.local.yml my-float-exporter ./float_exporter`
* You should see *my-float-exporter* running: `helm list`

To uninstall: `helm uninstall my-float-exporter`


# Run in Kubernetes
Run *float_exporter* as a servive in a Kubernetes cluster managed by *kubectl*.
This section refers to files in directory *k8s*.
All files uses namespace *monitoring*. If you want to use a different namespace,
you can change the configuration files accordingly.

* Clone repository
* Add namespace *monitoring*: `kubectl create -f fe-namespace.yml`
* Copy *fe-secret.yml* to *fe-secret.local.yml* and add your Float access token
* Create secret in Kubernetes: `kubectl create -f fe-secret.local.yml`
* Copy *fe-configmap.yml* to *fe-configmap.local.yml* and change to you liking. You must add a valid email.
* Create configmap in Kubernetes: `kubectl create -f fe-configmap.local.yml`
* Create the *fe-svc* service and *fe-dep* deployment in Kubernetes: `kubectl create -f fe-service.yml`
* Forward you local port 9709 to the *float_exporter* service: `kubectl port-forward -n monitoring service/fe-svc 9709:9709`
* You should be able to see your metrics at `http://localhost:9709/metrics`

When running, you should see a pod, a deployment (with replicaset) and a service in the *monitoring* namespace:

```
kubectl get all -n monitoring

NAME                                  READY   STATUS      RESTARTS   AGE...
pod/fe-dep-xxx-xxx                    1/1     Running     0          18h

NAME                           TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)     AGE
service/fe-svc                 ClusterIP   xx.xx.xx.xx      <none>        9709/TCP    18h

NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/fe-dep           1/1     1            1           18h

NAME                                        DESIRED   CURRENT   READY   AGE
replicaset.apps/fe-dep-xxxx                 1         1         1       18h
```




# Run locally

* Clone repository
* Install Python packages: `pip3 install -r requirements.txt`
* Copy config file *float_exporter.yml* to *float_exporter.local.yml*
* Update *float_exporter.local.yml* with your configuration.
* Run float_exporter.py: `./float_exporter.py ./float_exporter.local.yml`
* You should see the log from float_exporter confirming a successful run.
* You should be able to see your metrics at `http://localhost:9709/metrics`

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
* You should be able to see your metrics at `http://localhost:9709/metrics`

## Configuration with environment variables
If you don't want to map an external config file to the container, you can pass
environment variables for the container to use in stead of the values in the configuration
file */etc/float_config.yml*. Here is an example of setting
the access token to be used by *float_exporter*.

* `docker run --rm --env FLOAT_ACCESS_TOKEN=****** -p 9709:9709 float_exporter`

You should probably always use the flag *--rm* to remove the container when stopping float_exporter.
If you don't do that, you will end up with a lot of unused containers. If you want to keep the log file,
you should map an external directory to */var/log* in the container as a *volume*.

