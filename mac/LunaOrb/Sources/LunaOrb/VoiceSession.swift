import AVFoundation
import AppKit
import Speech

/// Live-Gespraech (Phase 17, M4) — Lunas Kern: zuhoeren, antworten, sprechen.
///
/// Bewusst **Halbduplex** fuer Robustheit: waehrend LUNA spricht, ist das Mikrofon AUS (kein Feedback-Loop,
/// kein fragiles Voice-Processing). Ablauf je Runde: Mikrofon (AVAudioEngine) -> SFSpeechRecognizer (de-DE)
/// -> bei Sprechpause Aeusserung an die lokale LUNA (`/api/chat`) -> Antwort per ElevenLabs (`/api/tts`,
/// Fallback System-Stimme) -> danach wieder zuhoeren. Jeder Schritt meldet seinen Status (onInfo) fuer
/// sichtbare Diagnose. Barge-in (Reinreden) kommt als spaetere Ausbaustufe (braucht Echo-Cancellation).
final class VoiceSession: NSObject, AVAudioPlayerDelegate, NSSpeechSynthesizerDelegate {
    enum State { case idle, listening, speaking }

    private let client: LunaClient
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "de-DE"))
    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private var player: AVAudioPlayer?
    private let synth = NSSpeechSynthesizer()

    private var silenceTimer: Timer?
    private var lastTranscript = ""
    private var active = false

    var onState: ((State) -> Void)?
    var onTranscript: ((String) -> Void)?
    var onInfo: ((String) -> Void)?

    init(client: LunaClient) {
        self.client = client
        super.init()
        synth.delegate = self
    }

    var isActive: Bool { active }

    // MARK: - Start/Stop

    func start(_ completion: @escaping (Bool) -> Void) {
        requestPermissions { [weak self] ok, why in
            guard let self = self else { return }
            guard ok else { self.onInfo?(why); completion(false); return }
            self.active = true
            self.startListening()
            completion(true)
        }
    }

    func stop() {
        active = false
        silenceTimer?.invalidate(); silenceTimer = nil
        player?.stop(); player = nil
        if synth.isSpeaking { synth.stopSpeaking() }
        teardownAudio()
        setState(.idle)
        onInfo?("Gespraech beendet.")
    }

    /// Reiner Ausgabe-Test (unabhaengig vom Mikrofon) — prueft, ob man LUNA hoert.
    func speakTest() {
        speak("Hallo, ich bin LUNA. Wenn du mich hoerst, funktioniert die Sprachausgabe.", resumeAfter: false)
    }

    private func requestPermissions(_ done: @escaping (Bool, String) -> Void) {
        SFSpeechRecognizer.requestAuthorization { auth in
            guard auth == .authorized else {
                DispatchQueue.main.async { done(false, "Spracherkennung nicht erlaubt (Datenschutz-Einstellungen).") }
                return
            }
            AVCaptureDevice.requestAccess(for: .audio) { micOK in
                DispatchQueue.main.async {
                    done(micOK, micOK ? "" : "Mikrofon nicht erlaubt (Datenschutz-Einstellungen).")
                }
            }
        }
    }

    // MARK: - Hoeren

    private func startListening() {
        guard active else { return }
        teardownAudio()

        guard let recognizer = recognizer, recognizer.isAvailable else {
            onInfo?("Spracherkennung de-DE nicht verfuegbar."); return
        }
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        request = req

        let input = engine.inputNode
        let format = input.inputFormat(forBus: 0)
        guard format.sampleRate > 0 else { onInfo?("Kein Mikrofon-Eingang gefunden."); return }
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
        }
        engine.prepare()
        do { try engine.start() } catch {
            onInfo?("Audio-Engine-Fehler: \(error.localizedDescription)"); return
        }
        setState(.listening)
        onInfo?("Ich hoere zu …")

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            guard let self = self else { return }
            if let result = result {
                let text = result.bestTranscription.formattedString
                if !text.isEmpty { self.handlePartial(text) }
            }
            if let error = error, self.active {
                // Haeufig nur ein Timeout/Abbruch — still neu aufsetzen, wenn nichts laeuft.
                NSLog("LUNA Voice recognition: %@", error.localizedDescription)
            }
        }
    }

    private func handlePartial(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        lastTranscript = trimmed
        onTranscript?(trimmed)
        // Sprechpause -> Aeusserung abgeschlossen.
        silenceTimer?.invalidate()
        silenceTimer = Timer.scheduledTimer(withTimeInterval: 1.2, repeats: false) { [weak self] _ in
            self?.finalizeUtterance()
        }
    }

    private func finalizeUtterance() {
        let utterance = lastTranscript
        lastTranscript = ""
        guard active, !utterance.isEmpty else { return }
        // Mikrofon AUS, waehrend LUNA denkt + spricht (Halbduplex).
        teardownAudio()
        setState(.idle)
        onInfo?("Verstanden: \(utterance)")
        client.chat(utterance) { [weak self] reply in
            self?.speak(reply, resumeAfter: true)
        }
    }

    private func teardownAudio() {
        silenceTimer?.invalidate(); silenceTimer = nil
        task?.cancel(); task = nil
        request?.endAudio(); request = nil
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
    }

    // MARK: - Sprechen

    private func speak(_ text: String, resumeAfter: Bool) {
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { if resumeAfter { startListening() }; return }
        setState(.speaking)
        onInfo?("LUNA antwortet …")
        resumeListeningAfterSpeaking = resumeAfter

        client.tts(clean) { [weak self] data in
            guard let self = self else { return }
            if let data = data, let p = try? AVAudioPlayer(data: data) {
                self.player = p
                p.delegate = self
                p.play()
            } else {
                // Fallback: macOS-System-Stimme.
                self.onInfo?("ElevenLabs nicht verfuegbar — System-Stimme.")
                self.synth.startSpeaking(clean)
                if !self.synth.isSpeaking { self.finishedSpeaking() }
            }
        }
    }

    private var resumeListeningAfterSpeaking = true

    private func finishedSpeaking() {
        player = nil
        if active && resumeListeningAfterSpeaking {
            startListening()
        } else {
            setState(.idle)
        }
    }

    // AVAudioPlayerDelegate
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async { [weak self] in self?.finishedSpeaking() }
    }

    // NSSpeechSynthesizerDelegate
    func speechSynthesizer(_ sender: NSSpeechSynthesizer, didFinishSpeaking finished: Bool) {
        DispatchQueue.main.async { [weak self] in self?.finishedSpeaking() }
    }

    // MARK: - Hilfen

    private func setState(_ s: State) {
        DispatchQueue.main.async { [weak self] in self?.onState?(s) }
    }
}
