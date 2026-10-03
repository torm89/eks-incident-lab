FROM python:3.12-slim

# Non-root user with a numeric ID, so Kubernetes can verify runAsNonRoot.
ARG APP_UID=10001
RUN useradd --uid ${APP_UID} --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

USER ${APP_UID}
EXPOSE 8080
CMD ["uvicorn", "ai_assistant.app:app", "--host", "0.0.0.0", "--port", "8080"]
