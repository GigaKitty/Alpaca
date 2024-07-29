

function cap_docker_compose_poke() {
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT stop $1
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT build $1
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT up -d $1
}

export ENVIRONMENT=core
cap_docker_compose_poke

export ENVIRONMENT=dev
cap_docker_compose_poke

export ENVIRONMENT=main
cap_docker_compose_poke