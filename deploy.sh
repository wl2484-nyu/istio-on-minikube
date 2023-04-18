DEPLOY_INFRA=$1
DEPLOY_APP=$2
PROFILE=e2e-1.0.0-1.0.0
NS=e2e
APP=e2e
SVC_1=e2e-1
SVC_2=e2e-2

if [[ $DEPLOY_INFRA == "TRUE" ]]
then
  # create cluster
  minikube profile $PROFILE
  minikube delete
  minikube start -p $PROFILE

  # default active profile to $APP
  minikube profile $PROFILE

  # install istio
  istioctl install --set profile=demo -y

  # install istio dashboard addons
  kubectl apply -f kubernetes/addons/prometheus.yaml
  kubectl patch svc prometheus -n istio-system -p '{"spec": {"type": "NodePort"}}'
  #minikube service prometheus -n istio-system --url
  kubectl apply -f kubernetes/addons/grafana.yaml
  kubectl patch svc grafana -n istio-system -p '{"spec": {"type": "NodePort"}}'
  #minikube service grafana -n istio-system --url
  kubectl apply -f kubernetes/addons/jaeger.yaml
  kubectl patch svc tracing -n istio-system -p '{"spec": {"type": "NodePort"}}'
  #minikube service tracing -n istio-system --url
  kubectl apply -f kubernetes/addons/kiali.yaml
  kubectl patch svc kiali -n istio-system -p '{"spec": {"type": "NodePort"}}'
  #minikube service kiali -n istio-system --url

  # enable addons
  minikube -p $PROFILE addons enable dashboard
  minikube -p $PROFILE addons enable metrics-server
  minikube -p $PROFILE addons enable istio
fi

if [[ $DEPLOY_APP == "TRUE" ]]
then
	# uninstall app
	helm uninstall $APP --namespace $NS
	sleep 5

	# build app image
	eval $(minikube -p $PROFILE docker-env)
	docker build -t $SVC_1 ./app/rolldice
	docker build -t $SVC_2 ./app/rolldice

	# package app
	mkdir -p charts/$APP/package
	PACKAGE=`helm package charts/$APP --destination charts/$APP/package --namespace $NS | cut -d':' -f2 | xargs`
	
	# create app namespace
	kubectl apply -f kubernetes/namespace/e2e.yaml

	# label node
	#kubectl label nodes $PROFILE node-affinity=true

	helm upgrade -i $APP $PACKAGE --namespace $NS -f charts/values.yaml

	# get pods
	sleep 5
	kubectl get pods -n $NS
fi
