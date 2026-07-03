# Instagram App-Review -- Einreichungs-Paket (Collab-CRM)

> Referenz fuer die Meta App-Review der Berechtigung `instagram_business_manage_messages`. Ziel: echte
> Kooperations-DMs von FREMDEN Accounts an @hanserautisch empfangen (im Dev-Modus liefert Meta nur Test-Events
> + DMs zwischen App-Rollen-Accounts). Texte fuers Meta-Formular auf Englisch (internationale Pruefer).

## Stand (2026-07-02)
- Technik komplett + live bewiesen: Webhook `https://os.hanserautisch.synology.me/api/webhook/instagram`,
  Signaturpruefung, robuster Parser, CrmStore, Klassifikation, To-do, Notifier -- Metas `messages`-Feldprobe
  kommt an und landet klassifiziert im CRM.
- **Business-Verifizierung: laeuft** (Meta „Wird ueberprueft", ~2 Werktage) -- Voraussetzung fuer die Review.
- Datenschutz-URL vorhanden (CEO). App-Icon/Kategorie/Datenloeschungs-URL vor Einreichung final pruefen.

## 1. Berechtigungen anfordern (Advanced Access)
- `instagram_business_basic`
- `instagram_business_manage_messages`

## 2. Use-Case-Beschreibung (Formularfeld)
AGENT-OS is an internal business assistant used by our company (Hanserautisch) to manage incoming Instagram
Direct Messages sent to our own Instagram professional account (@hanserautisch). We use
`instagram_business_manage_messages` to receive inbound DMs via webhook so we can automatically detect and
organize partnership/collaboration inquiries from other businesses into an internal CRM and surface prioritized
follow-up tasks to the account owner. The app does NOT send automated replies -- the owner replies personally.
This helps us avoid missing collaboration requests and respond faster. Message data is stored securely on our
own private server and is not shared with third parties.

## 3. Wie die Berechtigung genutzt wird (Detail-Feld)
When a user sends a Direct Message to our @hanserautisch account, Meta delivers a `messages` webhook event to
our server (https://os.hanserautisch.synology.me/api/webhook/instagram). The server verifies the payload
signature (X-Hub-Signature-256), stores the message text and sender ID in an internal CRM, classifies whether
it is a collaboration inquiry, and creates a follow-up task for the owner. No messages are sent by the app.

## 4. Pruefer-Anleitung (Step-by-step)
1. A user sends a DM to the @hanserautisch Instagram account.
2. The message is received server-side via the Messaging webhook.
3. It appears in our internal CRM dashboard (shown in the screencast), classified and with a follow-up task.

## 5. Screencast -- Drehbuch (WICHTIG)
Echte Fremd-DMs kommen im Dev-Modus nicht durch -> Screencast ueber den **Tester-Account** aufnehmen:
1. Zweiten Account als **Instagram-Tester** hinzufuegen (Rollen -> einladen -> in dessen IG-App annehmen).
2. Aufnahme starten: von diesem Tester-Account eine DM „Kooperationsanfrage ..." an @hanserautisch schicken.
3. Zu LUNA-OS -> App **Collab-CRM** wechseln -> neue Nachricht erscheint, als „kooperation" klassifiziert,
   mit To-do. Kurz erklaeren (Voiceover/Text).

## 6. App-Einstellungen final gegenpruefen
Datenschutz-URL (vorhanden) · Datenloeschungs-URL gesetzt · App-Icon hochgeladen · Kategorie gewaehlt
(z. B. „Messaging"/„Business") · Kontakt-E-Mail.

## 7. „Zulaessige Nutzung" -- Umfang & Feld-Texte (Stand 2026-07-03)

**Nur anfordern, was die App demonstrierbar tut** (sonst Ablehnung -- Meta verlangt je Berechtigung einen
passenden Screencast). Die App EMPFAENGT nur DMs (Webhook -> CRM/Klassifikation/To-do) und SENDET nichts.

- ✅ **behalten:** `instagram_business_basic`, `instagram_business_manage_messages`
- ❌ **aus dieser Einreichung entfernen:** **Human Agent** (App sendet/antwortet nicht) und
  `instagram_business_manage_insights` (keine IG-Analytics; das „insights" im Code ist unser internes Lagebild).
  -> spaetere, eigene Einreichungen, falls je „durch die App antworten" (Human Agent) bzw. Social-Media-
  Analyzer (Insights) gebaut wird.

**Feld „Beschreibe, wie deine App diese Berechtigung verwendet":**

*instagram_business_basic:*
> AGENT-OS uses instagram_business_basic to identify and access our own Instagram professional account
> (@hanserautisch) -- the account ID and username -- which is required to receive and correctly associate
> inbound Direct Messages delivered to that account. We do not access or store other users' profile data beyond
> the sender identifier attached to the messages they send us. This permission is a prerequisite for
> instagram_business_manage_messages.

*instagram_business_manage_messages:*
> AGENT-OS is an internal business tool for our own company (Hanserautisch). We use
> instagram_business_manage_messages to receive inbound Direct Messages sent to our own Instagram professional
> account (@hanserautisch) via the Messaging webhook. When a message arrives, our server verifies the payload
> signature (X-Hub-Signature-256), stores the message text and sender ID in our private internal CRM,
> automatically classifies whether it is a partnership/collaboration inquiry, and creates a prioritized
> follow-up task for the account owner. The app does NOT send any automated replies -- the owner reads and
> replies personally in the Instagram app. Message data is stored securely on our own private server and is
> never shared with third parties. Purpose: avoid missing collaboration requests and respond faster.

**Screencast:** EIN Video deckt beide Berechtigungen ab (Ablauf aus Abschnitt 5): Tester-Account schickt eine
Koop-DM an @hanserautisch -> in LUNA-OS App „Collab-CRM" erscheint sie klassifiziert mit To-do.

**Zustimmung:** Haekchen „Ich stimme der zulaessigen Nutzung zu" je Berechtigung setzen.

## Hinweise / Risiken
- Einzel-Konto-Tools koennen 1-2 Nachbesserungsrunden brauchen (Meta will klaren Messaging-Use-Case sehen).
- App-Secret = **Instagram-App-Geheimcode** (NICHT der Facebook-App-Geheimcode).
- Nach jedem `.env`-/Code-Change: `luna-os` neu starten. Deployment: `sync-to-nas.sh --no-restart` + Neustart.
