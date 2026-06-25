"""Einmalige OAuth-Autorisierung -> Refresh-Token fuer LUNA (Phase 11, Google Workspace).

Voraussetzung: `client_secret.json` eines OAuth-Desktop-Clients aus der Google Cloud Console
(siehe deploy/google-oauth-setup.md). Oeffnet den Browser zur Zustimmung mit dem separaten
LUNA-Google-Konto und druckt die drei Werte fuer orchestrator/.env.

Nutzung:
    pip install google-auth-oauthlib google-api-python-client
    python deploy/google_oauth_authorize.py /pfad/zu/client_secret.json

Die ausgegebenen Werte (CLIENT_ID/SECRET/REFRESH_TOKEN) NUR in orchestrator/.env eintragen --
niemals ins Repo committen.
"""
import json
import sys
from pathlib import Path

# SCOPES aus der kanonischen Quelle ziehen (muss zum Consent-Screen passen).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.governance.google_workspace import SCOPES  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Nutzung: python deploy/google_oauth_authorize.py <client_secret.json>")
        return 2
    secret_file = sys.argv[1]
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Bitte zuerst installieren: pip install google-auth-oauthlib google-api-python-client")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")  # erzwingt Refresh-Token

    info = json.loads(Path(secret_file).read_text())
    conf = info.get("installed") or info.get("web") or {}
    if not creds.refresh_token:
        print("FEHLER: Kein Refresh-Token erhalten. Client-Typ 'Desktop' nutzen und Zugriff neu zustimmen.")
        return 1

    print("\n--- In orchestrator/.env eintragen (Mac UND NAS, NICHT ins Repo) ---")
    print(f"GOOGLE_OAUTH_CLIENT_ID={conf.get('client_id', '')}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={conf.get('client_secret', '')}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
