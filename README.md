# dtp-final-project


## Environment Setups
1. install Docker

2. install Minikube

3. check Minikube status first
```shell
minikube status
```

4. configure default Minikube cpu & memory (default 2 cpu & 2GB mem) to align with requirements for Istio
> https://stackoverflow.com/questions/52199737/minikube-default-cpu-memory

```shell
minikube config set cpus 4
minikube config set memory 10240
cat ~/.minikube/config/config.json
```

4. start a multi-node minikube cluster
```shell
minikube start --nodes 3 -p poc-e2e
```

5. set active profile to poc-e2e
```shell
minikube profile poc-e2e
```

6. install Istio on Minikube
> useful refs:
> 
> https://kubebyexample.com/learning-paths/istio/install
> 
> https://kishoreteach.medium.com/set-up-istio-on-minikube-in-5-steps-get-sample-application-up-and-running-8396daf30dd6

7. enable required addons
```shell
minikube addons enable dashboard
minikube -p poc-e2e addons enable metrics-server
minikube addons enable registry
minikube addons enable istio
```

## Build Docker Image

### Docker at Local
```shell
eval $(minikube docker-env)
docker build -t poc-e2e .
```

### Minikube
```shell
minikube image build -t poc-e2e .
```

## Deployment Steps
```shell
# wget -P addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/prometheus.yaml
# kubectl apply -f addons/prometheus.yaml
# wget -P addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/grafana.yaml
# kubectl apply -f addons/grafana.yaml
# wget -P addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/jaeger.yaml
# kubectl apply -f addons/jaeger.yaml
# wget -P addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/kiali.yaml
# kubectl apply -f addons/kiali.yaml
kubectl apply -f namespace/e2e.yaml
kubectl apply -f services/e2e.yaml
kubectl apply -f deployments/e2e.yaml
kubectl apply -f deployments/e2e.yaml
kubectl apply -f ingress/e2e.yaml
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
kubectl describe limits mylimits --namespace=poc-e2e
```


## TODO
1. install elasticsearch on minikube
1. figure out trace aggregation
1. configure per-container cpu/memory limits


## Notes
1. When starting a minikube cluster with multiple nodes, image pulls fail on the second node (i.e. ErrImageNeverPull)
   > A known issue: https://github.com/kubernetes/minikube/issues/11505
