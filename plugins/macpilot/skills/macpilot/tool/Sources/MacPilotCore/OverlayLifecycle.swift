import Foundation

/// A display lease is refreshed only when an invocation selects its target.
/// It is independent of pointer persistence and preview visibility.
public struct OverlayTarget: Codable {
    public var observation: String
    public var activityAt: Double
    public var targetSequence: String
    public var ownerPID: Int32?
    public var ownerStartID: String?
    public var ownerTransport: String?
    public static let idleLimit: TimeInterval = 30

    public init(observation: String, activityAt: Double, targetSequence: String,
                ownerPID: Int32? = nil, ownerStartID: String? = nil, ownerTransport: String? = nil) {
        self.observation = observation; self.activityAt = activityAt; self.targetSequence = targetSequence
        self.ownerPID = ownerPID; self.ownerStartID = ownerStartID; self.ownerTransport = ownerTransport
    }
    public func endReason(now: Date = Date(), currentOwnerStartID: String?) -> String? {
        let age = now.timeIntervalSince1970 - activityAt
        guard activityAt.isFinite, age >= -1 else { return "invalid_activity_time" }
        guard age < Self.idleLimit else { return "idle_expired" }
        let hasOwner = ownerPID != nil || ownerStartID != nil || ownerTransport != nil
        if hasOwner {
            guard let ownerPID, ownerPID > 0, let ownerStartID, !ownerStartID.isEmpty, ownerTransport != nil else {
                return "invalid_owner"
            }
        }
        if ownerTransport == InvocationTransport.mcpStdio.rawValue {
            guard let ownerPID, ownerPID > 0, let ownerStartID, !ownerStartID.isEmpty,
                  currentOwnerStartID == ownerStartID else { return "owner_exited" }
        } else if ownerTransport != nil && ownerTransport != InvocationTransport.cli.rawValue {
            return "invalid_owner_transport"
        }
        return nil
    }
}
