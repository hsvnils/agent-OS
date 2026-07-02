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
#  - tzdata: Zeitzone Europe/Berlin fuer die Briefings (08:00/20:00)
#  - openai: Multi-Provider-Fallback fuer den Chat (Anthropic zuerst, OpenAI bei Engpass)
#  - pip-audit: Dependency-CVE-Scan fuer den Cybersecurity-Agent (Phase 21, sicherheits_audit)
RUN pip install --no-cache-dir "claude-agent-sdk==0.2.107" "anthropic==0.111.0" \
    "google-api-python-client==2.149.0" "google-auth==2.35.0" "tzdata" "openai" \
    "fastapi==0.138.0" "uvicorn==0.49.0" "pip-audit==2.10.1"

ENV PYTHONUNBUFFERED=1
# Git-Identitaet + safe.directory SYSTEMWEIT (/etc/gitconfig) -- gilt fuer JEDEN User, auch den
# Non-root-Runtime-User. safe.directory '*' verhindert "detected dubious ownership" (exit 128) beim
# Bind-Mount-Repo (Eigentuemer != Prozess), user.name/.email erlauben die Worktree-Commits der Execution.
RUN git config --system --add safe.directory /app \
 && git config --system --add safe.directory '*' \
 && git config --system user.email "luna@hanserautisch.local" \
 && git config --system user.name "LUNA"

# Non-root-Runtime-User. UID/GID an den NAS-Eigentuemer der Bind-Mount-Daten angeglichen
# (nilskrueger 1026 : users 100), damit der Prozess Repo + Daten-Stores lesen UND schreiben kann.
# Non-root erlaubt der gebundelten Claude-CLI `--dangerously-skip-permissions` OHNE den riskanten
# IS_SANDBOX-root-Bypass -> sichere Execution. HOME ist beschreibbar (CLI-/Git-Cache).
RUN groupadd -g 100 appusers 2>/dev/null || true \
 && useradd -u 1026 -g 100 -m -d /home/luna -s /bin/bash luna
ENV HOME=/home/luna
USER luna

WORKDIR /app
# Code/Daten kommen per Volume (siehe docker-compose.yml). Secrets liegen in orchestrator/.env (gemountet).
CMD ["python", "-m", "orchestrator.channels.telegram.bot"]
