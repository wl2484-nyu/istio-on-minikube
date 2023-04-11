# dtp-final-project

## Environment Setups

> Docker, Minikube, and istioctl are expected to be pre-installed at your local environment;
> Then the rest deployment steps are fully covered in `deploy.sh`.

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

9. install Helm

10. install elasticsearch
> https://www.bogotobogo.com/DevOps/Docker/Docker_Kubernetes_ElasticSearch_with_Helm_minikube.php
```shell
helm repo add elastic https://Helm.elastic.co
# helm repo list

# https://github.com/elastic/helm-charts/tree/main/elasticsearch/examples/minikube
# In order to properly support the required persistent volume claims for the Elasticsearch StatefulSet, the default-storageclass and storage-provisioner minikube addons must be enabled.
minikube addons enable default-storageclass
minikube addons enable storage-provisioner
#wget -P kubernetes/elasticsearch https://raw.githubusercontent.com/elastic/Helm-charts/master/elasticsearch/examples/minikube/values.yaml
helm upgrade -i elasticsearch elastic/elasticsearch -f kubernetes/elasticsearch/values.yaml
#    Release "kibana" does not exist. Installing it now.
#   NAME: elasticsearch
#   LAST DEPLOYED: Tue Apr 11 00:23:16 2023
#   NAMESPACE: default
#   STATUS: deployed
#   REVISION: 1
#   NOTES:
#   1. Watch all cluster members come up.
#     $ kubectl get pods --namespace=default -l app=elasticsearch-master -w
#   2. Retrieve elastic user's password.
#     $ kubectl get secrets --namespace=default elasticsearch-master-credentials -ojsonpath='{.data.password}' | base64 -d
#   3. Test cluster health using Helm test.
#     $ helm --namespace=default test elasticsearch
```

11. install kibana
> suggestions for installation failure: https://lightrun.com/answers/elastic-helm-charts-error-while-installing-kibana-851

```shell
helm upgrade -i kibana elastic/kibana
#   Release "kibana" does not exist. Installing it now.
#   NAME: kibana
#   LAST DEPLOYED: Tue Apr 11 00:57:19 2023
#   NAMESPACE: default
#   STATUS: deployed
#   REVISION: 1
#   TEST SUITE: None
#   NOTES:
#   1. Watch all containers come up.
#     $ kubectl get pods --namespace=default -l release=kibana -w
#   2. Retrieve the elastic user's password.
#     $ kubectl get secrets --namespace=default elasticsearch-master-credentials -ojsonpath='{.data.password}' | base64 -d
#   3. Retrieve the kibana service account token.
#     $ kubectl get secrets --namespace=default kibana-kibana-es-token -ojsonpath='{.data.token}' | base64 -d
```

12. install metricbeat
```shell
helm upgrade -i metricbeat elastic/metricbeat
#   Release "metricbeat" does not exist. Installing it now.
#   NAME: metricbeat
#   LAST DEPLOYED: Tue Apr 11 01:06:03 2023
#   NAMESPACE: default
#   STATUS: deployed
#   REVISION: 1
#   TEST SUITE: None
#   NOTES:
#   1. Watch all containers come up.
#     $ kubectl get pods --namespace=default -l app=metricbeat-metricbeat -w
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

1. install elasticsearch on minikube with helm (modified values)
1. explore kiali dashboard: https://medium.com/kialiproject/trace-my-mesh-part-1-3-35e252f9c6a9
1. figure out trace aggregation
1. evaluate suitable service type
1. configure per-container cpu/memory limits

## Notes

1. When starting a minikube cluster with multiple nodes, image pulls fail on the second node (i.e. ErrImageNeverPull)
   > A known issue: https://github.com/kubernetes/minikube/issues/11505
