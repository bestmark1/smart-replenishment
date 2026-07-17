# Deployment Guidelines

## 1. Local Containerized Deployment

You can run both the FastAPI API and the Streamlit dashboard locally inside containers using Docker Compose.

### Steps
1. Make sure you have Docker and Docker Compose installed and running.
2. Build and start the services:
   ```bash
   make compose-up
   ```
3. Docker Compose will:
   * Build the base image from the `Dockerfile`.
   * Start the `api` container on port `8000`.
   * Start the `dashboard` container on port `8501`.
   * Mount the `./data` and `./reports` directories as volumes so that the containers can read predictions and logs directly from your host machine.

4. To stop the containers:
   ```bash
   make compose-down
   ```

---

## 2. Cloud Production Deployment

For deploying the dashboard and API in a production cloud environment, we recommend:

### A. FastAPI API on Render or AWS ECS
* **Image Registry:** Build the Docker image and push it to AWS ECR or Docker Hub.
* **Serverless Containers:** Deploy using Render Web Services or AWS ECS Fargate.
* **Volume Mount / Storage:** Mount a persistent shared network disk or AWS S3 bucket to read the latest `final_test_forecast.parquet` and `priority_results.parquet` artifacts.

### B. Streamlit Dashboard on Streamlit Community Cloud or AWS
* **Community Cloud:** Directly link your public GitHub repository to Streamlit Community Cloud. Point it to `src/smart_replenishment/dashboard/app.py`.
* **Private Registry:** Alternatively, deploy the Streamlit container on ECS Fargate behind an Application Load Balancer.
