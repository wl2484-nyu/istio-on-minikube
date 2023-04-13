# Per Request Type Performance Anomaly Detection

# Progress
> Latest Update: `04/13/23`
## Done
TBA

## In-Progress
TBA

## Todo
TBA


# Requirements
1. Docker, Minikube, istioctl, and helm are required to be pre-installed at your local.
> Then the rest build and deployment steps can be fully covered in `deploy.sh`.

2. CPU & Memory of Minikube should be enlarged to align with Istio's requirements.
> https://stackoverflow.com/questions/52199737/minikube-default-cpu-memory

```shell
minikube config set cpus 4
minikube config set memory 10240
cat ~/.minikube/config/config.json
```


# Build & Deployment
The all-in-one scripts `deploy.sh` provides toggles to support both infra and app deployment.
```shell
./deploy.sh <DEPLOY_INFRA_TOGGLE> <DEPLOY_APP_TOGGLE>
```
* **DEPLOY_INFRA_TOGGLE**: `TRUE` or `FALSE`
* **DEPLOY_APP_TOGGLE**: `TRUE` or `FALSE`

## Deploy Infra
### Create Cluster
Create a Minikube single-node cluster, and set it to active.

```shell
PROFILE=poc-e2e

# create cluster
minikube profile $PROFILE
minikube delete
minikube start -p $PROFILE

# set $PROFILE to active
minikube profile $PROFILE
```

### Deploy Istio & Addon Dashboards
Deploy Istio and addon dashboards (such as prometheus, grafana, jaeger, and kiali).

```shell
PROFILE=poc-e2e

# install istio
istioctl install --set profile=default -y

# install istio dashboard addons
kubectl apply -f kubernetes/addons/prometheus.yaml
kubectl apply -f kubernetes/addons/grafana.yaml
kubectl apply -f kubernetes/addons/jaeger.yaml
kubectl apply -f kubernetes/addons/kiali.yaml

# enable addons
minikube -p $PROFILE addons enable dashboard
minikube -p $PROFILE addons enable metrics-server
minikube -p $PROFILE addons enable istio

# create namespace
kubectl apply -f kubernetes/namespace/poc-e2e.yaml
```

#### Access Dashboard
* Prometheus
```shell
kubectl patch svc prometheus -n istio-system -p '{"spec": {"type": "NodePort"}}'
minikube service prometheus -n istio-system --url
```

* Grafana
```shell
kubectl patch svc grafana -n istio-system -p '{"spec": {"type": "NodePort"}}'
minikube service grafana -n istio-system --url
```

* Jaeger
```shell
kubectl patch svc tracing -n istio-system -p '{"spec": {"type": "NodePort"}}'
minikube service tracing -n istio-system --url
```

* Kiali
```shell
kubectl patch svc kiali -n istio-system -p '{"spec": {"type": "NodePort"}}'
minikube service kiali -n istio-system --url
```


## Deploy App
Rollout the latest app release, which include uninstall, build, package, and deploy the app.

### Uninstall App
```shell
APP=poc-e2e
NS=poc-e2e

helm uninstall $APP --namespace $NS
```

### Build App Image
```shell
APP=poc-e2e

eval $(minikube -p poc-e2e docker-env)
docker build -t poc-e2e ./app
```

### Package App
```shell
APP=poc-e2e
NS=poc-e2e

mkdir -p charts/$APP/package
PACKAGE=`helm package charts/$APP --destination charts/$APP/package --namespace $NS | cut -d':' -f2 | xargs`
```

### Deploy App
```shell
APP=poc-e2e
NS=poc-e2e

helm upgrade -i $APP $PACKAGE --namespace $NS -f charts/values.yaml
```


# Access Service API

## Requirements
Create a secure network tunnel between local machine and the kubernetes cluster running on Minikube
```shell
minikube tunnel --cleanup
```

## Approach 1
Curl service API with port-forward.

### Command
```shell
kubectl port-forward svc/<SERVICE_NAME> -n <NAMESPACE> <LOCAL_PORT>:<CONTAINER_PORT>
```
* `CONTAINER_PORT`: `spec.containers.ports.containerPort` defined in the Deployment YAML

### Example
```shell
kubectl port-forward svc/poc-e2e-1 -n poc-e2e 5566:5566
kubectl port-forward svc/poc-e2e-2 -n poc-e2e 5567:5566
```

## Approach 2
Curl service API with Host in header.
> Not generating opentelemetry traces to Jaeger.

### Command
```shell
curl -H "Host: <SERVICE_ENDPOINT>" http://localhost:<PORT>/<API_PATH>
```
* **PORT**: `spec.servers.port.number` defined in the Gateway YAML

### Example
```shell
curl -H "Host: poc-e2e-2.dtp.com" http://localhost/rolldice
```
* Need not specify `PORT` if its value is 80


# Test at Local

## App
```shell
cd app
docker build -t poc-e2e .
docker run -p 30000:5566 poc-e2e
curl http://localhost:30000/rolldice
```

## OpenTelemetry Collector

```shell
docker run -p 4317:4317 \
    --network=host \
    -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
    otel/opentelemetry-collector:latest \
    --config=/etc/otel-collector-config.yaml
```

# Useful Debugging CMDs
```shell
kubectl describe pod $pod_name
kubectl logs $pod_name
kubectl exec -it $pod_name -- bin/bash
```

# Other Notes
1. When starting a minikube cluster with multiple nodes, image pulls fail on the second node (i.e. ErrImageNeverPull)
   > A known issue: https://github.com/kubernetes/minikube/issues/11505
