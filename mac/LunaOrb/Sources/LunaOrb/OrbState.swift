import AppKit

/// Die drei sichtbaren Zustaende des Orbs (wie in LUNA-OS): ruhig / hoert zu / spricht.
enum OrbState {
    case idle
    case listening
    case speaking

    var symbolName: String {
        switch self {
        case .idle: return "moonphase.waning.crescent"
        case .listening: return "waveform"
        case .speaking: return "waveform.circle.fill"
        }
    }

    var tint: NSColor {
        switch self {
        case .idle: return NSColor.secondaryLabelColor
        case .listening: return NSColor.systemTeal
        case .speaking: return NSColor.systemGreen
        }
    }
}
