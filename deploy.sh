DEPLOY_INFRA=$1
DEPLOY_APP=$2
PROFILE=e2e-1.1.0-1.0.1
NS=e2e
SYS=e2e
APP_1=rolldice-1
APP_2=rolldice-2

if [[ $DEPLOY_INFRA == "TRUE" ]]
then
  # create cluster
  minikube profile $PROFILE
  minikube delete
  minikube start -p $PROFILE

  # default active profile to $PROFILE
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
	helm uninstall $SYS --namespace $NS
	sleep 5

	# build app image
	eval $(minikube -p $PROFILE docker-env)
	docker build -t $APP_1 ./app/rolldice
	docker build -t $APP_2 ./app/rolldice

	# package sys app
	mkdir -p charts/$SYS/package
	PACKAGE=`helm package charts/$SYS --destination charts/$SYS/package --namespace $NS | cut -d':' -f2 | xargs`
	
	# create sys namespace
	kubectl apply -f kubernetes/namespace/e2e.yaml

	# label node
	#kubectl label nodes $PROFILE node-affinity=true

	helm upgrade -i $SYS $PACKAGE --namespace $NS -f charts/values.yaml

	# get pods
	sleep 5
	kubectl get pods -n $NS
fi
