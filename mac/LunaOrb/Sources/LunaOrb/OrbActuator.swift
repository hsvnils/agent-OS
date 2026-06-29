import AppKit
import ApplicationServices

/// Native „Haende" des Orbs (Phase 17, M5/#3). Fuehrt Tastatur-/Maus-Aktionen via CGEvent aus —
/// das funktioniert nur, wenn der CEO dem Orb-`.app` die Berechtigung **Bedienungshilfen/Accessibility**
/// erteilt hat (sonst klare Rueckmeldung). Der Python-Server (Verstand + Tor) legt Befehle als Dateien in
/// `~/.luna_orb/` ab; der Orb fuehrt sie aus und schreibt das Ergebnis zurueck (`res-<id>.json`).
final class OrbActuator {
    private let dir = (NSHomeDirectory() as NSString).appendingPathComponent(".luna_orb")
    private var timer: Timer?

    // US-ANSI-Tastencodes fuer Kuerzel (taste).
    private let keyCodes: [String: CGKeyCode] = [
        "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11,
        "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21,
        "6": 22, "5": 23, "9": 25, "7": 26, "8": 28, "0": 29, "o": 31, "u": 32, "i": 34, "p": 35,
        "l": 37, "j": 38, "k": 40, "n": 45, "m": 46,
        "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51,
        "escape": 53, "esc": 53, "left": 123, "right": 124, "down": 125, "up": 126,
    ]

    func start() {
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        timer = Timer.scheduledTimer(withTimeInterval: 0.15, repeats: true) { [weak self] _ in
            self?.scan()
        }
    }

    /// Berechtigung Bedienungshilfen anfragen (zeigt den System-Dialog).
    @discardableResult
    func requestAccessibility() -> Bool {
        let opt = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        return AXIsProcessTrustedWithOptions([opt: true] as CFDictionary)
    }

    var accessibilityGranted: Bool { AXIsProcessTrusted() }

    // MARK: - Datei-Queue

    private func scan() {
        let fm = FileManager.default
        guard let items = try? fm.contentsOfDirectory(atPath: dir) else { return }
        for name in items where name.hasPrefix("cmd-") && name.hasSuffix(".json") {
            let id = String(name.dropFirst(4).dropLast(5))
            let cmdPath = (dir as NSString).appendingPathComponent(name)
            let data = (try? Data(contentsOf: URL(fileURLWithPath: cmdPath))) ?? Data()
            try? fm.removeItem(atPath: cmdPath)
            let cmd = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
            let result = execute(cmd)
            let resPath = (dir as NSString).appendingPathComponent("res-\(id).json")
            if let out = try? JSONSerialization.data(withJSONObject: result) {
                try? out.write(to: URL(fileURLWithPath: resPath))
            }
        }
    }

    private func execute(_ cmd: [String: Any]) -> [String: Any] {
        let typ = (cmd["typ"] as? String) ?? ""
        // Tastatur/Maus brauchen Bedienungshilfen.
        if ["tippen", "taste", "klick"].contains(typ) && !accessibilityGranted {
            return ["ok": false, "grund": "Bedienungshilfen (Accessibility) fuer LUNA Orb nicht erlaubt."]
        }
        switch typ {
        case "tippen":
            type((cmd["text"] as? String) ?? "")
            return ["ok": true]
        case "taste":
            return shortcut((cmd["kuerzel"] as? String) ?? "")
        case "klick":
            let x = (cmd["x"] as? Double) ?? Double((cmd["x"] as? Int) ?? -1)
            let y = (cmd["y"] as? Double) ?? Double((cmd["y"] as? Int) ?? -1)
            return click(x: x, y: y)
        default:
            return ["ok": false, "grund": "Unbekannter Befehl: \(typ)"]
        }
    }

    // MARK: - CGEvent-Primitive

    private func type(_ s: String) {
        guard !s.isEmpty else { return }
        let src = CGEventSource(stateID: .combinedSessionState)
        let utf16 = Array(s.utf16)
        let down = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: true)
        down?.keyboardSetUnicodeString(stringLength: utf16.count, unicodeString: utf16)
        down?.post(tap: .cghidEventTap)
        let up = CGEvent(keyboardEventSource: src, virtualKey: 0, keyDown: false)
        up?.keyboardSetUnicodeString(stringLength: utf16.count, unicodeString: utf16)
        up?.post(tap: .cghidEventTap)
    }

    private func shortcut(_ kuerzel: String) -> [String: Any] {
        let teile = kuerzel.lowercased().replacingOccurrences(of: " ", with: "")
            .split(separator: "+").map(String.init).filter { !$0.isEmpty }
        guard let key = teile.last, let code = keyCodes[key] else {
            return ["ok": false, "grund": "Taste '\(kuerzel)' nicht erkannt."]
        }
        var flags: CGEventFlags = []
        for m in teile.dropLast() {
            switch m {
            case "cmd", "command": flags.insert(.maskCommand)
            case "shift": flags.insert(.maskShift)
            case "opt", "option", "alt": flags.insert(.maskAlternate)
            case "ctrl", "control": flags.insert(.maskControl)
            default: break
            }
        }
        let src = CGEventSource(stateID: .combinedSessionState)
        let down = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: true)
        down?.flags = flags
        down?.post(tap: .cghidEventTap)
        let up = CGEvent(keyboardEventSource: src, virtualKey: code, keyDown: false)
        up?.flags = flags
        up?.post(tap: .cghidEventTap)
        return ["ok": true]
    }

    private func click(x: Double, y: Double) -> [String: Any] {
        guard x >= 0, y >= 0 else { return ["ok": false, "grund": "Ungueltige Koordinaten."] }
        let pt = CGPoint(x: x, y: y)
        let src = CGEventSource(stateID: .combinedSessionState)
        CGEvent(mouseEventSource: src, mouseType: .mouseMoved, mouseCursorPosition: pt, mouseButton: .left)?
            .post(tap: .cghidEventTap)
        CGEvent(mouseEventSource: src, mouseType: .leftMouseDown, mouseCursorPosition: pt, mouseButton: .left)?
            .post(tap: .cghidEventTap)
        CGEvent(mouseEventSource: src, mouseType: .leftMouseUp, mouseCursorPosition: pt, mouseButton: .left)?
            .post(tap: .cghidEventTap)
        return ["ok": true]
    }
}
