# Подготовка к деплою на отдельный VPS

## Принцип

В production попадает только inference-контур: FastAPI, Streamlit и два готовых Parquet-файла. M5-датасет, DuckDB-витрина и обучение моделей на VPS не хранятся и не запускаются. Это необходимо для небольшой VPS: обучение на миллионах строк требует существенно больше RAM, чем чтение готовых прогнозов.

## Что требуется определить до выкладки

1. SSH-алиас или IP **целевого** сервера.
2. Домен/поддомен и доступ к его DNS-зоне для HTTPS.
3. Доступные RAM, диск, Docker и reverse proxy на целевом сервере.
4. Свободный внутренний Docker network или отдельный reverse proxy; нельзя копировать имя сети, Caddyfile и порты от другого production-проекта.
5. Актуальные локальные артефакты:
   - `data/processed/final_test_forecast.parquet`;
   - `data/processed/priority_results.parquet`.

## Локальная подготовка

На Apple Silicon образ для типичной x86_64 VPS необходимо собирать под её архитектуру:

```bash
docker buildx build --platform linux/amd64 --load -t smart-replenishment:latest .
docker image save smart-replenishment:latest | gzip > /tmp/smart-replenishment-image.tar.gz
```

`docker image save` создаёт переносимый архив образа, а `docker image load` восстанавливает его на VPS. `.dockerignore` исключает исходные данные и артефакты из образа: их передают отдельным read-only volume.

## Обязательная проверка после выкладки

1. Контейнеры запущены и имеют status `healthy`.
2. Внутренний `GET /health` API подтверждает, что оба Parquet-артефакта загружены.
3. Публичный HTTPS-URL открывается, фильтры дашборда и график SKU работают в браузере.
4. На сервере не выполнялись команды обучения, а исходный M5-датасет отсутствует.

Точные Compose- и reverse-proxy-конфигурации создаются только после аудита целевого сервера.
