# LUNA -- Telegram-Bot fuer 24/7-Betrieb (z. B. auf Synology DS923+, x86-64 / Docker).
# Schlankes Image: nur was der Telegram-Kanal braucht (kein Pipecat/Voice).
# Der Repo-Code + Daten (+ orchestrator/.env, + .git fuer Execution) werden per Bind-Mount eingehaengt.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Laufzeit-Abhaengigkeiten des Telegram-Kanals:
#  - claude-agent-sdk: delegate + Execution-Engine (gebundelte CLI, Linux-Build)
#  - anthropic: konversationelles HoA-Gehirn (Tool-Loop)
#  - google-api-python-client + google-auth: Google Workspace (Phase 11; nur aktiv mit OAuth-Credentials)
RUN pip install --no-cache-dir "claude-agent-sdk==0.2.107" "anthropic==0.111.0" \
    "google-api-python-client==2.149.0" "google-auth==2.35.0"

ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Code/Daten kommen per Volume (siehe docker-compose.yml). Secrets liegen in orchestrator/.env (gemountet).
CMD ["python", "-m", "orchestrator.channels.telegram.bot"]
