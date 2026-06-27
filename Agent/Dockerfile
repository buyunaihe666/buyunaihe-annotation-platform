FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

# Default: agent-web via gunicorn (production).
# For dev: override CMD to `python run_agent.py`.
# For agent-worker: override CMD to `python run_audit_worker.py`.
# For DB migrate (one-shot): override CMD to `python -m annotation_agent.migrate`.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "app:app"]