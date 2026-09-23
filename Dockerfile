FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY trip_planner ./trip_planner

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "trip_planner.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
