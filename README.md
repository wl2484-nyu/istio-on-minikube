# Per Request Type Performance Profiling

## Introduction
TBA

## Design
TBA

## Requirements
1. Docker, Minikube, istioctl, and helm are required to be pre-installed at your local.
> Then the rest build and deployment steps can be fully covered in `deploy.sh`.

2. CPU & Memory of Minikube should be enlarged to align with Istio's requirements.
> https://stackoverflow.com/questions/52199737/minikube-default-cpu-memory

```shell
minikube config set cpus 4
minikube config set memory 10240
cat ~/.minikube/config/config.json
```

## Build
```shell
eval $(minikube -p poc-e2e docker-env)
docker build -t poc-e2e ./app
```

## Deployment

### Create Minikube Cluster
```shell
PROFILE=poc-e2e

# create cluster
minikube profile $PROFILE
minikube delete
minikube start -p $PROFILE

# set $PROFILE to active
minikube profile $PROFILE
```

### Deploy Infra
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

### Deploy App
```shell
APP=poc-e2e
NS=poc-e2e

# uninstall app
helm uninstall $APP --namespace $NS
sleep 5

# package app
mkdir -p charts/$APP/package
PACKAGE=`helm package charts/$APP --destination charts/$APP/package --namespace $NS | cut -d':' -f2 | xargs`

# label node
#kubectl label nodes $PROFILE node-affinity=true

# deploy app
helm upgrade -i $APP $PACKAGE --namespace $NS -f charts/values.yaml
```

## Test at Local

### App
```shell
cd app
docker build -t poc-e2e .
docker run -p 30000:5566 poc-e2e
curl http://localhost:30000/rolldice
```

### OpenTelemetry Collector

```shell
docker run -p 4317:4317 \
    --network=host \
    -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
    otel/opentelemetry-collector:latest \
    --config=/etc/otel-collector-config.yaml
```

## Useful Debugging CMDs
```shell
kubectl describe pod $pod_name
kubectl logs $pod_name
kubectl exec -it $pod_name -- bin/bash
```

## TODO
1. explore kiali dashboard: https://medium.com/kialiproject/trace-my-mesh-part-1-3-35e252f9c6a9
1. define trace aggregation workflow: es or kiali
1. evaluate suitable service type (optional)
1. configure per-container cpu/memory limits (optional)
1. discuss poster/report content

## Notes

1. When starting a minikube cluster with multiple nodes, image pulls fail on the second node (i.e. ErrImageNeverPull)
   > A known issue: https://github.com/kubernetes/minikube/issues/11505
