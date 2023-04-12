CREATE_CLUSTER=$1
DEPLOY_APP=$2
PROFILE=poc-e2e
APP=poc-e2e
NS=poc-e2e

if [[ $CREATE_CLUSTER == "TRUE" ]]
then
  # create cluster
  minikube profile $PROFILE
  minikube delete
  minikube start -p $PROFILE

  # default active profile to $APP
  minikube profile $PROFILE

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
fi

if [[ $DEPLOY_APP == "TRUE" ]]
then
	# build
	eval $(minikube -p $PROFILE docker-env)
	docker build -t $APP ./app

	# deploy app
	kubectl apply -f kubernetes/namespace/poc-e2e.yaml
	kubectl apply -f kubernetes/services/poc-e2e.yaml
	kubectl apply -f kubernetes/deployments/poc-e2e.yaml
	kubectl apply -f kubernetes/deployments/poc-e2e.yaml
	kubectl apply -f kubernetes/ingress/poc-e2e.yaml

	# get pods
	sleep 5
	kubectl get pods -n $NS
fi
