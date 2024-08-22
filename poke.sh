environments=("core" "dev" "main")


function cap_docker_compose_poke() {
  ENVIRONMENT=$1
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT stop
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT build
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT up -d
}

function cap_docker_compose_down() {
  ENVIRONMENT=$1
  docker-compose --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT down
}


for env in "${environments[@]}"; do
    echo "Processing environment: $env"
    
    # Check if the function should be called
    if [ "$1" == "poke" ]; then
        cap_docker_compose_poke $env
    elif [ "$1" == "down" ]; then
        cap_docker_compose_down $env
    else
        echo "Invalid argument. Please use 'poke' or 'down'."
        exit 1
    fi
done