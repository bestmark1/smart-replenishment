# Деплой на VPS без обучения модели

## Назначение

В продакшен попадает только inference-контур: FastAPI, Streamlit и два готовых Parquet-файла. M5-датасет, DuckDB-витрина и обучение моделей на VPS не хранятся и не запускаются. Это принципиально для небольшой VPS: обучение на миллионах строк требует существенно больше RAM, чем показ дашборда и чтение 4 МБ готовых прогнозов.

## Что требуется до выкладки

1. DNS-запись `A` для `replenishment.fitmentor-ai.ru` должна указывать на VPS. Без неё Caddy не сможет выпустить HTTPS-сертификат.
2. На VPS должен существовать Docker network `fitmentor_default`: она уже используется reverse proxy Caddy.
3. Локально должны быть актуальные артефакты:
   - `data/processed/final_test_forecast.parquet`;
   - `data/processed/priority_results.parquet`.
4. Docker-образ необходимо собрать локально под архитектуру VPS (`linux/amd64`). Не собирайте и не обучайте модель на VPS.

## Локальная подготовка образа

На Apple Silicon обязательно укажите архитектуру VPS:

```bash
docker buildx build --platform linux/amd64 --load -t smart-replenishment:latest .
docker image save smart-replenishment:latest | gzip > /tmp/smart-replenishment-image.tar.gz
```

`docker image save` создаёт переносимый архив образа, а `docker image load` восстанавливает его на VPS. Не включайте в образ папку `data/`: `.dockerignore` специально исключает исходные данные и артефакты.

## Передача на VPS

```bash
ssh my-vps 'mkdir -p /opt/smart-replenishment/data/processed'

scp /tmp/smart-replenishment-image.tar.gz my-vps:/tmp/
scp docker-compose.vps.yml my-vps:/opt/smart-replenishment/docker-compose.yml
scp data/processed/final_test_forecast.parquet my-vps:/opt/smart-replenishment/data/processed/
scp data/processed/priority_results.parquet my-vps:/opt/smart-replenishment/data/processed/

ssh my-vps '
  docker image load -i /tmp/smart-replenishment-image.tar.gz &&
  rm /tmp/smart-replenishment-image.tar.gz &&
  cd /opt/smart-replenishment &&
  docker compose up -d
'
```

## Reverse proxy

`deploy/Caddyfile.fragment` содержит отдельный virtual host для дашборда. Его блок нужно добавить в `/opt/FitMentor/Caddyfile` **только после появления DNS-записи**, затем проверить конфигурацию внутри контейнера и мягко перезагрузить Caddy:

```bash
docker exec fitmentor_caddy caddy validate --config /etc/caddy/Caddyfile
docker exec fitmentor_caddy caddy reload --config /etc/caddy/Caddyfile
```

Контейнеры Smart Replenishment не открывают внешние порты. Caddy получает к ним доступ по внутренней Docker network `fitmentor_default`; наружу остаются доступны только 80/443.

## Проверка после выкладки

```bash
ssh my-vps 'cd /opt/smart-replenishment && docker compose ps'
ssh my-vps 'docker exec smart_replenishment_api python -c "import urllib.request; print(urllib.request.urlopen(\"http://127.0.0.1:8000/health\").read().decode())"'
curl --fail --silent --show-error https://replenishment.fitmentor-ai.ru/_stcore/health
```

После этого откройте публичный URL в браузере, переключите магазин и департамент, выберите SKU и убедитесь, что отрисовался график. Проверьте также, что FitMentor продолжает отвечать на свой health endpoint.

## Откат

Если новый проект влияет на память или Caddy не может получить сертификат:

```bash
ssh my-vps 'cd /opt/smart-replenishment && docker compose down'
```

Удалите только добавленный блок `replenishment.fitmentor-ai.ru` из Caddyfile и перезагрузите Caddy. Не выполняйте `docker system prune` и не перезапускайте весь `/opt/FitMentor` ради этого проекта.
