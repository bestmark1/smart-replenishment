# Деплой на VPS без обучения модели

## Архитектурное решение

Целевой сервер — `185.79.138.118`. На нём уже работает Traefik в Docker network `web_gateway`, поэтому Smart Replenishment разворачивается как отдельный Compose-проект и не открывает новые внешние порты. Планируемый адрес дашборда:

```text
https://smart-replenishment.185.79.138.118.nip.io
```

`nip.io` автоматически сопоставляет hostname с IP-адресом, поэтому отдельная DNS-запись и покупка домена не нужны. Traefik получает HTTPS-сертификат через существующий ACME resolver.

## Что попадает на сервер

Только inference-контур:

- Docker image `smart-replenishment` для `linux/amd64`;
- `data/processed/final_test_forecast.parquet`;
- `data/processed/priority_results.parquet`;
- `docker-compose.vps.yml` и `.env` с hostname.

На VPS **не** передаются M5-датасет, DuckDB-витрина, модели для обучения и train/evaluate/simulate пайплайн. Контейнеры читают артефакты через read-only mount. Лимиты памяти: API 256 МБ, Streamlit dashboard 384 МБ.

## Локальная сборка образа

VPS использует `x86_64`; на Mac с Apple Silicon образ надо собирать под `linux/amd64`:

```bash
docker buildx build --platform linux/amd64 --load -t smart-replenishment:latest .
docker image save smart-replenishment:latest | gzip > /tmp/smart-replenishment-image.tar.gz
```

## Передача и запуск

```bash
ssh root@185.79.138.118 'mkdir -p /opt/apps/smart-replenishment/data/processed'

scp /tmp/smart-replenishment-image.tar.gz root@185.79.138.118:/tmp/
scp docker-compose.vps.yml root@185.79.138.118:/opt/apps/smart-replenishment/docker-compose.yml
scp deploy/vps.env.example root@185.79.138.118:/opt/apps/smart-replenishment/.env
scp data/processed/final_test_forecast.parquet root@185.79.138.118:/opt/apps/smart-replenishment/data/processed/
scp data/processed/priority_results.parquet root@185.79.138.118:/opt/apps/smart-replenishment/data/processed/

ssh root@185.79.138.118 '
  set -e
  docker image load -i /tmp/smart-replenishment-image.tar.gz
  rm /tmp/smart-replenishment-image.tar.gz
  cd /opt/apps/smart-replenishment
  docker compose up -d
'
```

## Проверка и откат

```bash
ssh root@185.79.138.118 'cd /opt/apps/smart-replenishment && docker compose ps'
ssh root@185.79.138.118 'docker exec smart_replenishment_api python -c "import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8000/health\").read().decode())"'
curl --fail --silent --show-error https://smart-replenishment.185.79.138.118.nip.io/_stcore/health
```

После проверки endpoint откройте публичный URL в браузере, смените магазин и департамент, выберите SKU и убедитесь, что строится график. При проблеме откат затрагивает только этот проект:

```bash
ssh root@185.79.138.118 'cd /opt/apps/smart-replenishment && docker compose down'
```

Не выполняйте `docker system prune`, не открывайте дополнительные порты и не меняйте конфигурацию Traefik ради этого проекта.
