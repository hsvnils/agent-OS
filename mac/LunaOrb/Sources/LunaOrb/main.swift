import AppKit

/// LUNA am Mac — Menueleisten-Orb (Phase 17, M1).
/// Lebt als Accessory-App in der Menueleiste (kein Dock-Icon), zeigt den Orb mit drei
/// Zustaenden und spricht mit der LOKALEN LUNA (127.0.0.1). Steuerung/Awareness folgen in M2/M3.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private let client = LunaClient()
    private let orbActuator = OrbActuator()
    private lazy var voice = VoiceSession(client: client)
    private var state: OrbState = .idle {
        didSet { renderOrb() }
    }
    private var serverOnline: Bool?
    private var lastVoiceInfo: String = ""

    /// Not-Aus-Flag, das der Python-Aktuator vor jeder Aktion prueft.
    private let killSwitchPath = (NSHomeDirectory() as NSString)
        .appendingPathComponent(".luna_orb_killswitch")

    /// Steuerungs-Modus-Datei (gemeinsam mit dem Python-Aktuator): "sofort" | "bestaetigen".
    private let modePath = (NSHomeDirectory() as NSString)
        .appendingPathComponent(".luna_orb_mode")

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        configureVoice()
        orbActuator.start()
        renderOrb()
        rebuildMenu()
        refreshServerStatus()
    }

    private func configureVoice() {
        voice.onState = { [weak self] s in
            switch s {
            case .idle: self?.state = .idle
            case .listening: self?.state = .listening
            case .speaking: self?.state = .speaking
            }
        }
        voice.onInfo = { [weak self] msg in
            self?.lastVoiceInfo = msg
            self?.rebuildMenu()
            NSLog("LUNA Voice: %@", msg)
        }
        voice.onTranscript = { [weak self] text in
            self?.lastVoiceInfo = "Gehört: " + text
            self?.rebuildMenu()
        }
    }

    // MARK: - Orb-Darstellung

    private func renderOrb() {
        guard let button = statusItem.button else { return }
        let img = NSImage(systemSymbolName: state.symbolName, accessibilityDescription: "LUNA")
        img?.isTemplate = (state == .idle)
        button.image = img
        button.contentTintColor = (state == .idle) ? nil : state.tint
    }

    // MARK: - Menue

    private func rebuildMenu() {
        let menu = NSMenu()

        let title = NSMenuItem(title: "LUNA am Mac", action: nil, keyEquivalent: "")
        title.isEnabled = false
        menu.addItem(title)
        menu.addItem(.separator())

        let statusText: String
        switch serverOnline {
        case .some(true): statusText = "Lokale LUNA: verbunden"
        case .some(false): statusText = "Lokale LUNA: offline (Port 8765?)"
        case .none: statusText = "Lokale LUNA: prüfe…"
        }
        let statusLine = NSMenuItem(title: statusText, action: nil, keyEquivalent: "")
        statusLine.isEnabled = false
        menu.addItem(statusLine)

        if !lastVoiceInfo.isEmpty {
            let info = NSMenuItem(title: "Stimme: " + lastVoiceInfo, action: nil, keyEquivalent: "")
            info.isEnabled = false
            menu.addItem(info)
        }

        let voiceOn = voice.isActive
        let voiceItem = NSMenuItem(
            title: voiceOn ? "Gespräch beenden" : "Live-Gespräch starten",
            action: #selector(toggleVoice), keyEquivalent: "g")
        voiceItem.target = self
        voiceItem.isEnabled = (serverOnline != false)
        voiceItem.state = voiceOn ? .on : .off
        menu.addItem(voiceItem)

        let test = NSMenuItem(title: "Stimme testen", action: #selector(testVoice), keyEquivalent: "t")
        test.target = self
        test.isEnabled = (serverOnline != false)
        menu.addItem(test)

        let talk = NSMenuItem(title: "Mit LUNA tippen…", action: #selector(askLuna), keyEquivalent: "l")
        talk.target = self
        talk.isEnabled = (serverOnline != false)
        menu.addItem(talk)

        let see = NSMenuItem(title: "Was siehst du?", action: #selector(seeScreen), keyEquivalent: "s")
        see.target = self
        see.isEnabled = (serverOnline != false)
        menu.addItem(see)

        let recheck = NSMenuItem(title: "Verbindung prüfen", action: #selector(refreshServerStatus), keyEquivalent: "r")
        recheck.target = self
        menu.addItem(recheck)

        menu.addItem(.separator())

        let instant = currentModeIsInstant()
        let modeItem = NSMenuItem(
            title: instant ? "Modus: Sofort-Umsetzung (EIN)" : "Modus: Erst bestätigen (Standard)",
            action: #selector(toggleMode), keyEquivalent: "")
        modeItem.target = self
        modeItem.state = instant ? .on : .off
        modeItem.toolTip = "Sofort-Modus: benigne, freigegebene Aktionen ohne Rückfrage. "
            + "Geld/Recht/Öffentlichkeit/Löschen bleiben immer bestätigungspflichtig."
        menu.addItem(modeItem)

        let axGranted = orbActuator.accessibilityGranted
        let ax = NSMenuItem(
            title: axGranted ? "Steuerung: erlaubt (Bedienungshilfen)" : "Steuerung erlauben (Bedienungshilfen)…",
            action: #selector(grantControl), keyEquivalent: "")
        ax.target = self
        ax.state = axGranted ? .on : .off
        menu.addItem(ax)

        let killActive = FileManager.default.fileExists(atPath: killSwitchPath)
        let kill = NSMenuItem(title: killActive ? "Not-Aus AKTIV — aufheben" : "Not-Aus (Steuerung sperren)",
                              action: #selector(toggleKillSwitch), keyEquivalent: "")
        kill.target = self
        menu.addItem(kill)

        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Beenden", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quit)

        statusItem.menu = menu
    }

    // MARK: - Aktionen

    @objc private func toggleVoice() {
        if voice.isActive {
            voice.stop()
            rebuildMenu()
        } else {
            voice.start { [weak self] ok in
                if !ok {
                    let a = NSAlert()
                    a.messageText = "Live-Gespräch nicht möglich"
                    a.informativeText = "Bitte Mikrofon und Spracherkennung erlauben "
                        + "(Systemeinstellungen → Datenschutz & Sicherheit)."
                    a.runModal()
                }
                self?.rebuildMenu()
            }
        }
    }

    @objc private func testVoice() {
        voice.speakTest()
    }

    @objc private func seeScreen() {
        lastVoiceInfo = "Schaue auf den Bildschirm …"
        rebuildMenu()
        Task { [weak self] in
            let png = await ScreenReader.capturePNG()
            await MainActor.run {
                guard let self = self else { return }
                guard let png = png else {
                    self.lastVoiceInfo = "Bildschirmaufnahme nicht erlaubt (Systemeinstellungen → "
                        + "Datenschutz & Sicherheit → Bildschirmaufnahme)."
                    self.rebuildMenu()
                    return
                }
                self.client.sehen(png.base64EncodedString(), "") { text in
                    self.lastVoiceInfo = "Bildschirm gelesen."
                    self.rebuildMenu()
                    self.showReply(text)
                }
            }
        }
    }

    @objc private func refreshServerStatus() {
        rebuildMenu()
        client.ping { [weak self] online in
            self?.serverOnline = online
            self?.rebuildMenu()
        }
    }

    @objc private func askLuna() {
        let alert = NSAlert()
        alert.messageText = "Was soll LUNA tun?"
        alert.informativeText = "Tipp-Nachricht an die lokale LUNA. Für das gesprochene Live-Gespräch den Orb-Menüpunkt Live-Gespräch starten verwenden."
        alert.addButton(withTitle: "Senden")
        alert.addButton(withTitle: "Abbrechen")

        let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24))
        input.placeholderString = "z. B. In welcher App bin ich gerade?"
        alert.accessoryView = input
        alert.window.initialFirstResponder = input

        guard alert.runModal() == .alertFirstButtonReturn else { return }
        let text = input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        state = .listening
        client.chat(text) { [weak self] reply in
            self?.state = .speaking
            self?.showReply(reply)
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { self?.state = .idle }
        }
    }

    private func showReply(_ reply: String) {
        let alert = NSAlert()
        alert.messageText = "LUNA"
        alert.informativeText = reply
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    private func currentModeIsInstant() -> Bool {
        let raw = (try? String(contentsOfFile: modePath, encoding: .utf8)) ?? ""
        return raw.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == "sofort"
    }

    @objc private func toggleMode() {
        let next = currentModeIsInstant() ? "bestaetigen" : "sofort"
        try? (next + "\n").write(toFile: modePath, atomically: true, encoding: .utf8)
        rebuildMenu()
    }

    @objc private func grantControl() {
        if orbActuator.accessibilityGranted {
            let a = NSAlert()
            a.messageText = "Steuerung ist erlaubt"
            a.informativeText = "LUNA darf Tastatur und Maus bedienen (Bedienungshilfen)."
            a.runModal()
            return
        }
        orbActuator.requestAccessibility()
        // Direkt zum richtigen Einstellungs-Bereich.
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
            NSWorkspace.shared.open(url)
        }
        rebuildMenu()
    }

    @objc private func toggleKillSwitch() {
        let fm = FileManager.default
        if fm.fileExists(atPath: killSwitchPath) {
            try? fm.removeItem(atPath: killSwitchPath)
        } else {
            let stamp = ISO8601DateFormatter().string(from: Date())
            try? "not-aus aktiviert: \(stamp)\n".write(toFile: killSwitchPath, atomically: true, encoding: .utf8)
            state = .idle
        }
        rebuildMenu()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
