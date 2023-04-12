# dtp-final-project

## Environment Setups

> Docker, Minikube, istioctl, and helm are expected to be installed at your local environment.
> Then the rest build and deployment steps can be fully covered in `deploy.sh`.

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
minikube start -p poc-e2e
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

given istioctl installed:

```shell
istioctl install --set profile=default -y
```

7. install Istio addons

```shell
# wget -P kubernetes/addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/prometheus.yaml
kubectl apply -f kubernetes/addons/prometheus.yaml
# wget -P kubernetes/addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/grafana.yaml
kubectl apply -f kubernetes/addons/grafana.yaml
# wget -P kubernetes/addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/jaeger.yaml
kubectl apply -f kubernetes/addons/jaeger.yaml
# wget -P kubernetes/addons https://raw.githubusercontent.com/istio/istio/release-1.17/samples/addons/kiali.yaml
kubectl apply -f kubernetes/addons/kiali.yaml
```

8. enable required addons

```shell
minikube -p poc-e2e addons enable dashboard
minikube -p poc-e2e addons enable metrics-server
minikube -p poc-e2e addons enable istio
```

## App Build

```shell
eval $(minikube -p poc-e2e docker-env)
docker build -t poc-e2e ./app
```

## App Deployment

```shell
kubectl apply -f kubernetes/namespace/e2e.yaml
kubectl apply -f kubernetes/services/e2e.yaml
kubectl apply -f kubernetes/deployments/e2e.yaml
kubectl apply -f kubernetes/deployments/e2e.yaml
kubectl apply -f kubernetes/ingress/e2e.yaml
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
