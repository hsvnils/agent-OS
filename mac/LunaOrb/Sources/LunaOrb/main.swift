import AppKit

/// LUNA am Mac — Menueleisten-Orb (Phase 17, M1).
/// Lebt als Accessory-App in der Menueleiste (kein Dock-Icon), zeigt den Orb mit drei
/// Zustaenden und spricht mit der LOKALEN LUNA (127.0.0.1). Steuerung/Awareness folgen in M2/M3.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private let client = LunaClient()
    private var state: OrbState = .idle {
        didSet { renderOrb() }
    }

    /// Not-Aus-Flag, das der (kuenftige) Python-Aktuator vor jeder Aktion prueft.
    private let killSwitchPath = (NSHomeDirectory() as NSString)
        .appendingPathComponent(".luna_orb_killswitch")

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        renderOrb()
        rebuildMenu(serverOnline: nil)
        refreshServerStatus()
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

    private func rebuildMenu(serverOnline: Bool?) {
        let menu = NSMenu()

        let title = NSMenuItem(title: "LUNA am Mac", action: nil, keyEquivalent: "")
        title.isEnabled = false
        menu.addItem(title)
        menu.addItem(.separator())

        let statusText: String
        switch serverOnline {
        case .some(true): statusText = "Lokale LUNA: verbunden"
        case .some(false): statusText = "Lokale LUNA: offline (Port 8765?)"
        case .none: statusText = "Lokale LUNA: pruefe…"
        }
        let statusLine = NSMenuItem(title: statusText, action: nil, keyEquivalent: "")
        statusLine.isEnabled = false
        menu.addItem(statusLine)

        let talk = NSMenuItem(title: "Mit LUNA sprechen…", action: #selector(askLuna), keyEquivalent: "l")
        talk.target = self
        talk.isEnabled = (serverOnline != false)
        menu.addItem(talk)

        let recheck = NSMenuItem(title: "Verbindung pruefen", action: #selector(refreshServerStatus), keyEquivalent: "r")
        recheck.target = self
        menu.addItem(recheck)

        menu.addItem(.separator())

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

    @objc private func refreshServerStatus() {
        rebuildMenu(serverOnline: nil)
        client.ping { [weak self] online in
            self?.rebuildMenu(serverOnline: online)
        }
    }

    @objc private func askLuna() {
        let alert = NSAlert()
        alert.messageText = "Was soll LUNA tun?"
        alert.informativeText = "Live-Co-Working (M1): Nachricht an die lokale LUNA. Steuerung/Awareness folgen."
        alert.addButton(withTitle: "Senden")
        alert.addButton(withTitle: "Abbrechen")

        let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24))
        input.placeholderString = "z. B. Was kannst du gerade?"
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

    @objc private func toggleKillSwitch() {
        let fm = FileManager.default
        if fm.fileExists(atPath: killSwitchPath) {
            try? fm.removeItem(atPath: killSwitchPath)
        } else {
            let stamp = ISO8601DateFormatter().string(from: Date())
            try? "not-aus aktiviert: \(stamp)\n".write(toFile: killSwitchPath, atomically: true, encoding: .utf8)
            state = .idle
        }
        rebuildMenu(serverOnline: nil)
        refreshServerStatus()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
