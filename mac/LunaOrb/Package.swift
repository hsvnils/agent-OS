// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "LunaOrb",
    platforms: [
        .macOS(.v14)
    ],
    targets: [
        .executableTarget(
            name: "LunaOrb",
            path: "Sources/LunaOrb",
            linkerSettings: [
                // Info.plist in das Binary einbetten, damit macOS-TCC die Mikrofon-/Sprach-
                // Berechtigungstexte findet (sonst Absturz beim ersten Zugriff).
                .unsafeFlags([
                    "-Xlinker", "-sectcreate",
                    "-Xlinker", "__TEXT",
                    "-Xlinker", "__info_plist",
                    "-Xlinker", "Info.plist",
                ])
            ]
        )
    ]
)
