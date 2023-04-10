CREATE_CLUSTER=$1
APP=poc-e2e

if [[ $CREATE_CLUSTER == "TRUE" ]]
then
  # create cluster
  minikube profile $APP
  minikube delete
  minikube start -p $APP

  # default active profile to $APP
  minikube profile $APP

  # install istio
  istioctl install --set profile=default -y

  # install istio dashboard addons
  kubectl apply -f kubernetes/addons/prometheus.yaml
  kubectl apply -f kubernetes/addons/grafana.yaml
  kubectl apply -f kubernetes/addons/jaeger.yaml
  kubectl apply -f kubernetes/addons/kiali.yaml

  # enable addons
  minikube -p $APP addons enable dashboard
  minikube -p $APP addons enable metrics-server
  minikube -p $APP addons enable istio
fi

# build
eval $(minikube -p $APP docker-env)
docker build -t $APP ./app

# deploy app
kubectl apply -f kubernetes/namespace/e2e.yaml
kubectl apply -f kubernetes/services/e2e.yaml
kubectl apply -f kubernetes/deployments/e2e.yaml
kubectl apply -f kubernetes/deployments/e2e.yaml
kubectl apply -f kubernetes/ingress/e2e.yaml

# get pods
sleep 5
kubectl get pods -n $APP
