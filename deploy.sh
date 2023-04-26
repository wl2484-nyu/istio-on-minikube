DEFAULT_SYS=multi-svc
TOY_SYS=toy
PROFILE=e2e-2.0.0-1.1.2
NS=e2e

DEPLOY_INFRA=$1
DEPLOY_APP=$2
SYS="${3:-$DEFAULT_SYS}"


if [[ $DEPLOY_INFRA == "TRUE" ]]
then
  # re-create a new cluster
  minikube delete --all
  minikube start -p "$PROFILE"

  # default active profile to $PROFILE
  minikube profile "$PROFILE"

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
  minikube -p "$PROFILE" addons enable dashboard
  minikube -p "$PROFILE" addons enable metrics-server
  minikube -p "$PROFILE" addons enable istio
fi

if [[ $SYS == "$DEFAULT_SYS" ]]
then
  # build & deploy scripts for the multi-svc apps

  if [[ $DEPLOY_APP == "TRUE" ]]
  then
    DEFAULT_MODULE_NAME=main
    DEFAULT_APP_NAME=app
    DEFAULT_PORT=5566

    # build app image
    eval "$(minikube -p $PROFILE docker-env)"
    for i in a b; do
      mkdir -p "app/svcs/svc_$i";
      cp "app/svcs/svc_$i.py" "app/svcs/svc_$i/main.py"
      cp "app/svcs/performance_tracer.py" "app/svcs/svc_$i/"
      cp "app/svcs/Dockerfile.template" "app/svcs/svc_$i/Dockerfile"
      cp "app/svcs/requirements.txt.template" "app/svcs/svc_$i/requirements.txt"
      docker build --build-arg DEFAULT_MODULE_NAME=$DEFAULT_MODULE_NAME --build-arg DEFAULT_APP_NAME=$DEFAULT_APP_NAME --build-arg DEFAULT_PORT=$DEFAULT_PORT -t "svc-$i" "./app/svcs/svc_$i";
    done

    # create sys namespace
    kubectl apply -f "kubernetes/namespace/$NS.yaml"

    # uninstall app
    helm uninstall "$SYS" --namespace "$NS"
    sleep 5

    # package sys app
    mkdir -p "charts/$SYS/package"
    PACKAGE=$(helm package "charts/$SYS" --destination "charts/$SYS/package" --namespace "$NS" | cut -d':' -f2 | xargs)

    # label node
    #kubectl label nodes "$PROFILE" node-affinity=true

    helm upgrade -i "$SYS" "$PACKAGE" --namespace "$NS" -f "charts/values.$SYS.yaml"

    # get pods
    sleep 5
    kubectl get pods -n "$NS"
  fi

elif [[ $SYS == "$TOY_SYS" ]]
then
  # build & deploy scripts for the rolldice toy app

  if [[ $DEPLOY_APP == "TRUE" ]]
  then
    DEFAULT_MODULE_NAME=main
    DEFAULT_APP_NAME=app
    DEFAULT_PORT=5566
    APP_A=rolldice-a
    APP_B=rolldice-b

    # build app image
    eval "$(minikube -p $PROFILE docker-env)"
    docker build --build-arg DEFAULT_MODULE_NAME=$DEFAULT_MODULE_NAME --build-arg DEFAULT_APP_NAME=$DEFAULT_APP_NAME --build-arg DEFAULT_PORT=$DEFAULT_PORT -t $APP_A ./app/rolldice
    docker build --build-arg DEFAULT_MODULE_NAME="$DEFAULT_MODULE_NAME" --build-arg DEFAULT_APP_NAME="$DEFAULT_APP_NAME" --build-arg DEFAULT_PORT="$DEFAULT_PORT" -t $APP_B ./app/rolldice

    # create sys namespace
    kubectl apply -f "kubernetes/namespace/$NS.yaml"

    # uninstall app
    helm uninstall "$SYS" --namespace "$NS"
    sleep 5

    # package sys app
    mkdir -p "charts/$SYS/package"
    PACKAGE=$(helm package "charts/$SYS" --destination "charts/$SYS/package" --namespace "$NS" | cut -d':' -f2 | xargs)

    # label node
    #kubectl label nodes "$PROFILE" node-affinity=true

    helm upgrade -i "$SYS" "$PACKAGE" --namespace "$NS" -f "charts/values.$SYS.yaml"

    # get pods
    sleep 5
    kubectl get pods -n "$NS"
  fi

else
  echo "SYS=$SYS not found!"
fi
