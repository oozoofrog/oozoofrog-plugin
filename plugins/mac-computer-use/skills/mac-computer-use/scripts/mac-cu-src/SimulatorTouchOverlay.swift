import AppKit

/// Input coordinates already follow the shown rotation; only the viewer's fit and flipped y remain.
func simulatorTouchPosition(_ point: CGPoint, viewport: CGRect, screen: CGSize) -> CGPoint? {
    guard screen.width > 0, screen.height > 0, viewport.width > 0, viewport.height > 0 else { return nil }
    let scale = min(viewport.width / screen.width, viewport.height / screen.height)
    return CGPoint(x: viewport.midX + (point.x - screen.width / 2) * scale,
                   y: viewport.midY - (point.y - screen.height / 2) * scale)
}

/// Viewer-only feedback. These layers never hit-test or change the simulator's pixels or input.
final class SimulatorTouchOverlay {
    let layer = CALayer()
    private var markers: [Int: CALayer] = [:]
    private var positions: [Int: CGPoint] = [:]
    private var lifts: [Int: UUID] = [:]
    private var screen = CGSize(width: 1, height: 1)

    init() { layer.zPosition = 10; layer.masksToBounds = true }

    func layout(viewport: CGRect, screen: CGSize) {
        layer.frame = viewport
        self.screen = screen
        for (id, point) in positions { markers[id]?.position = simulatorTouchPosition(point, viewport: layer.bounds, screen: screen) ?? .zero }
    }

    func update(_ contacts: [GestureContact]) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let active = Set(contacts.filter(\.touching).map(\.id))
        for contact in contacts where contact.touching {
            let marker = markers[contact.id] ?? makeMarker(contact.id)
            markers[contact.id] = marker
            positions[contact.id] = contact.point
            lifts[contact.id] = nil
            marker.removeAnimation(forKey: "lift")
            marker.opacity = 1
            marker.position = simulatorTouchPosition(contact.point, viewport: layer.bounds, screen: screen) ?? .zero
        }
        for (id, marker) in markers where !active.contains(id) && lifts[id] == nil {
            if let last = contacts.first(where: { $0.id == id }) {
                positions[id] = last.point
                marker.position = simulatorTouchPosition(last.point, viewport: layer.bounds, screen: screen) ?? .zero
            }
            let token = UUID()
            lifts[id] = token
            marker.opacity = 0
            let fade = CABasicAnimation(keyPath: "opacity")
            fade.fromValue = 1; fade.toValue = 0; fade.duration = 0.22
            marker.add(fade, forKey: "lift")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.22) { [weak self] in
                guard let self, self.lifts[id] == token else { return }
                marker.removeFromSuperlayer()
                self.markers[id] = nil; self.positions[id] = nil; self.lifts[id] = nil
            }
        }
        CATransaction.commit()
    }

    func clear() {
        markers.values.forEach { $0.removeFromSuperlayer() }
        markers = [:]; positions = [:]; lifts = [:]
    }

    private func makeMarker(_ id: Int) -> CALayer {
        let marker = CALayer()
        marker.bounds = CGRect(x: 0, y: 0, width: 36, height: 36)
        marker.cornerRadius = 18
        let colors: [NSColor] = [.systemBlue, .systemPink, .systemOrange]
        marker.backgroundColor = colors[(id - 1) % colors.count].withAlphaComponent(0.65).cgColor
        marker.borderColor = NSColor.white.cgColor; marker.borderWidth = 2
        marker.shadowColor = NSColor.black.cgColor; marker.shadowOpacity = 0.45; marker.shadowRadius = 3
        let number = CATextLayer()
        number.string = "\(id)"; number.font = NSFont.systemFont(ofSize: 17, weight: .bold); number.fontSize = 17
        number.foregroundColor = NSColor.white.cgColor; number.alignmentMode = .center
        number.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        number.frame = CGRect(x: 0, y: 7, width: 36, height: 23)
        marker.addSublayer(number)
        layer.addSublayer(marker)
        return marker
    }
}
