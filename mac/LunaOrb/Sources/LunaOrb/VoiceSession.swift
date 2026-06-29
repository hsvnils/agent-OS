import AVFoundation
import AppKit
import Speech

/// Live-Gespraech (Phase 17, M4) — Lunas Kern: zuhoeren, antworten, unterbrechbar (Barge-in).
///
/// Pipeline: Mikrofon (AVAudioEngine, Voice-Processing = Echo-Cancellation) -> SFSpeechRecognizer (de-DE)
/// -> bei Sprechpause die Aeusserung an die lokale LUNA (`/api/chat`) -> Antwort per ElevenLabs (`/api/tts`,
/// Fallback System-Stimme). Waehrend LUNA spricht, hoert sie weiter; echte Sprache des CEO stoppt die
/// Wiedergabe sofort (Barge-in).
final class VoiceSession: NSObject, AVAudioPlayerDelegate {
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
    private var speaking = false
    private var active = false

    /// Zustands-/Fehler-Callbacks fuer Orb + Menue (immer Main-Thread).
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

    /// Fragt Berechtigungen an und startet die Hoer-Schleife. completion(false) bei fehlender Erlaubnis.
    func start(_ completion: @escaping (Bool) -> Void) {
        requestPermissions { [weak self] ok in
            guard let self = self else { return }
            guard ok else { self.onInfo?("Mikrofon-/Spracherkennung nicht erlaubt."); completion(false); return }
            self.active = true
            self.beginListening()
            completion(true)
        }
    }

    func stop() {
        active = false
        stopSpeaking()
        silenceTimer?.invalidate(); silenceTimer = nil
        task?.cancel(); task = nil
        request?.endAudio(); request = nil
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
        setState(.idle)
    }

    private func requestPermissions(_ done: @escaping (Bool) -> Void) {
        SFSpeechRecognizer.requestAuthorization { auth in
            let speechOK = (auth == .authorized)
            AVCaptureDevice.requestAccess(for: .audio) { micOK in
                DispatchQueue.main.async { done(speechOK && micOK) }
            }
        }
    }

    // MARK: - Hoeren

    private func beginListening() {
        guard active else { return }
        // frische Erkennung je Aeusserung (vermeidet das ~1-Minuten-Limit der Engine).
        task?.cancel(); task = nil
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        request = req

        let input = engine.inputNode
        // Echo-Cancellation: damit das Mikro nicht Lunas eigene Stimme aufnimmt (echtes Barge-in).
        try? input.setVoiceProcessingEnabled(true)
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
        }
        engine.prepare()
        do { try engine.start() } catch {
            onInfo?("Audio-Engine-Fehler: \(error.localizedDescription)"); return
        }
        setState(.listening)

        guard let recognizer = recognizer, recognizer.isAvailable else {
            onInfo?("Spracherkennung de-DE nicht verfügbar."); return
        }
        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            guard let self = self else { return }
            if let result = result {
                let text = result.bestTranscription.formattedString
                self.handlePartial(text)
            }
            if error != nil, self.active, !self.speaking {
                // Erkennung neu aufsetzen (z. B. nach Timeout).
                self.restartListeningSoon()
            }
        }
    }

    private func handlePartial(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        lastTranscript = trimmed
        onTranscript?(trimmed)

        // Barge-in: spricht der CEO, waehrend LUNA redet -> Wiedergabe sofort stoppen.
        if speaking, trimmed.split(separator: " ").count >= 2 {
            stopSpeaking()
            setState(.listening)
        }

        // Sprechpause -> Aeusserung als abgeschlossen werten.
        silenceTimer?.invalidate()
        silenceTimer = Timer.scheduledTimer(withTimeInterval: 1.3, repeats: false) { [weak self] _ in
            self?.finalizeUtterance()
        }
    }

    private func finalizeUtterance() {
        let utterance = lastTranscript
        lastTranscript = ""
        guard active, !utterance.isEmpty else { return }
        // Erkennung pausieren, waehrend LUNA denkt/antwortet.
        task?.cancel(); task = nil
        request?.endAudio(); request = nil

        client.chat(utterance) { [weak self] reply in
            self?.speak(reply)
        }
    }

    private func restartListeningSoon() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
            guard let self = self, self.active, !self.speaking else { return }
            self.beginListening()
        }
    }

    // MARK: - Sprechen

    private func speak(_ text: String) {
        guard active else { return }
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { restartListeningSoon(); return }
        speaking = true
        setState(.speaking)
        // Waehrend des Sprechens weiter zuhoeren (Barge-in).
        beginListening()

        client.tts(clean) { [weak self] data in
            guard let self = self, self.speaking else { return }
            if let data = data, let p = try? AVAudioPlayer(data: data) {
                self.player = p
                p.delegate = self
                p.play()
            } else {
                // Fallback: System-Stimme (kein ElevenLabs verfuegbar).
                self.synth.startSpeaking(clean)
            }
        }
    }

    private func stopSpeaking() {
        speaking = false
        player?.stop(); player = nil
        if synth.isSpeaking { synth.stopSpeaking() }
    }

    private func finishedSpeaking() {
        guard speaking else { return }
        speaking = false
        guard active else { return }
        setState(.listening)
        // Hoeren laeuft bereits (beginListening in speak); zur Sicherheit neu aufsetzen, falls beendet.
        if task == nil { beginListening() }
    }

    // AVAudioPlayerDelegate
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async { [weak self] in self?.finishedSpeaking() }
    }

    // MARK: - Hilfen

    private func setState(_ s: State) {
        DispatchQueue.main.async { [weak self] in self?.onState?(s) }
    }
}

extension VoiceSession: NSSpeechSynthesizerDelegate {
    func speechSynthesizer(_ sender: NSSpeechSynthesizer, didFinishSpeaking finished: Bool) {
        DispatchQueue.main.async { [weak self] in self?.finishedSpeaking() }
    }
}
