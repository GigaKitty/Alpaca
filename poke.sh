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

function cap_docker_compose_it() {
  ENVIRONMENT=$1
  docker-compose -it --env-file .env-$ENVIRONMENT --profile $ENVIRONMENT -p $ENVIRONMENT --entrypoint /bin/bash $1
}
 
function backup_core() {
  docker run --rm -v redis_data:/volume -v $(pwd)/_data/backups:/backup busybox sh -c "cd /volume && tar czf /backup/redis_data_$(date +%Y%m%d).tar.gz ."
  docker run --rm -v grafana_data:/volume -v $(pwd)/_data/backups:/backup busybox sh -c "cd /volume && tar czf /backup/grafana_data_$(date +%Y%m%d).tar.gz ."
  docker run --rm -v influxdb_data:/volume -v $(pwd)/_data/backups:/backup busybox sh -c "cd /volume && tar czf /backup/influxdb_data_$(date +%Y%m%d).tar.gz ."
}


if [ "$1" == "poke" ]; then
  for env in "${environments[@]}"; do
    echo "Processing environment: $env"
    cap_docker_compose_poke $env
  done
elif [ "$1" == "down" ]; then
  for env in "${environments[@]}"; do
    echo "Processing environment: $env"
    cap_docker_compose_down $env
  done
elif [ "$1" == "backup" ]; then
    backup_core
elif [ "$1" == "it" ]; then
  for env in "${environments[@]}"; do
    echo "Processing environment: $env"
    cap_docker_compose_it $env
  done
else
    echo "Invalid argumen."
    exit 1
fi