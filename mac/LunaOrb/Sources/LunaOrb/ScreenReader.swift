import AppKit
import ScreenCaptureKit

/// Bildschirm-Aufnahme (Phase 17, M5/#3) — die „Augen" des Orbs.
///
/// Nimmt per ScreenCaptureKit einen Screenshot auf (braucht die Berechtigung **Bildschirmaufnahme**,
/// die der CEO dem Orb-`.app` einmal erteilt) und liefert PNG-Daten. Der Server (`/api/sehen`) gibt das
/// Bild an ein Vision-Modell (Gemini) -> LUNA „sieht", was auf dem Schirm ist.
enum ScreenReader {
    /// Screenshot des Hauptbildschirms als PNG. nil bei fehlender Berechtigung/Fehler.
    static func capturePNG() async -> Data? {
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false,
                                                                                onScreenWindowsOnly: true)
            guard let display = content.displays.first else { return nil }
            let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
            let config = SCStreamConfiguration()
            // Auf Punktgroesse begrenzen (Retina nicht in voller Pixelzahl -> kleinere Payload).
            config.width = display.width
            config.height = display.height
            let cgImage = try await SCScreenshotManager.captureImage(contentFilter: filter,
                                                                     configuration: config)
            let rep = NSBitmapImageRep(cgImage: cgImage)
            return rep.representation(using: .png, properties: [:])
        } catch {
            NSLog("LUNA ScreenReader: %@", error.localizedDescription)
            return nil
        }
    }
}
