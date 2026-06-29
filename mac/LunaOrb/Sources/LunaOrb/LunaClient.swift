import Foundation

/// Duenner Client zur LOKALEN LUNA (orchestrator/channels/web), nur 127.0.0.1.
/// Spricht /api/chat (Body {message, history} -> {reply}) und prueft Erreichbarkeit.
final class LunaClient {
    /// Basis-URL der lokalen LUNA. Ueberschreibbar via Env LUNA_LOCAL_URL.
    let baseURL: URL

    init() {
        let raw = ProcessInfo.processInfo.environment["LUNA_LOCAL_URL"] ?? "http://127.0.0.1:8765"
        self.baseURL = URL(string: raw) ?? URL(string: "http://127.0.0.1:8765")!
    }

    /// Erreichbarkeit der lokalen LUNA (GET /). Antwort auf dem Main-Thread.
    func ping(_ done: @escaping (Bool) -> Void) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/"))
        req.httpMethod = "GET"
        req.timeoutInterval = 3
        URLSession.shared.dataTask(with: req) { _, resp, err in
            let ok = (err == nil) && ((resp as? HTTPURLResponse)?.statusCode ?? 500) < 500
            DispatchQueue.main.async { done(ok) }
        }.resume()
    }

    /// Eine Nachricht an LUNA schicken. Antworttext (oder Fehlertext) auf dem Main-Thread.
    func chat(_ message: String, _ done: @escaping (String) -> Void) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/api/chat"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 60
        let payload: [String: Any] = ["message": message, "history": []]
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)

        URLSession.shared.dataTask(with: req) { data, _, err in
            var reply = "(keine Antwort)"
            if let err = err {
                reply = "Verbindungsfehler: \(err.localizedDescription)"
            } else if let data = data,
                      let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let r = obj["reply"] as? String, !r.isEmpty {
                reply = r
            }
            DispatchQueue.main.async { done(reply) }
        }.resume()
    }

    /// LUNAs Augen: Screenshot (base64-PNG) + optionale Frage -> Beschreibung via Vision-Modell.
    func sehen(_ base64: String, _ frage: String, _ done: @escaping (String) -> Void) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/api/sehen"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 60
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["bild_base64": base64, "frage": frage])
        URLSession.shared.dataTask(with: req) { data, _, err in
            var text = "Konnte den Bildschirm nicht lesen."
            if let err = err {
                text = "Verbindungsfehler: \(err.localizedDescription)"
            } else if let data = data,
                      let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                if let t = obj["text"] as? String, !t.isEmpty { text = t }
                else if let g = obj["grund"] as? String, !g.isEmpty { text = g }
            }
            DispatchQueue.main.async { done(text) }
        }.resume()
    }

    /// LUNAs ElevenLabs-Stimme: Text -> MP3-Daten. nil, wenn TTS nicht verfuegbar (Fallback Browser/System).
    func tts(_ text: String, _ done: @escaping (Data?) -> Void) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/api/tts"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 30
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["text": text])
        URLSession.shared.dataTask(with: req) { data, resp, err in
            let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
            let ok = err == nil && code == 200 && (data?.isEmpty == false)
            DispatchQueue.main.async { done(ok ? data : nil) }
        }.resume()
    }
}
