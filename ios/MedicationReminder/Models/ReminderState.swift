import Foundation

enum ReminderStatus: String, Codable {
    case pending
    case childMarkedTaken = "child_marked_taken"
    case adultConfirmed = "adult_confirmed"

    var displayText: String {
        switch self {
        case .pending: return "Not taken yet"
        case .childMarkedTaken: return "Waiting for a parent to confirm"
        case .adultConfirmed: return "Confirmed"
        }
    }
}

enum Role: String, Codable {
    case guardian
    case child
}

struct ReminderState: Codable, Equatable {
    let childId: String
    let dateKey: String
    let status: ReminderStatus
    let screenTimeShouldBeRestricted: Bool
    let reminderStartsAt: String
    let childMarkedAt: String?
    let adultConfirmedAt: String?

    enum CodingKeys: String, CodingKey {
        case childId = "child_id"
        case dateKey = "date_key"
        case status
        case screenTimeShouldBeRestricted = "screen_time_should_be_restricted"
        case reminderStartsAt = "reminder_starts_at"
        case childMarkedAt = "child_marked_at"
        case adultConfirmedAt = "adult_confirmed_at"
    }
}

struct ChildProfile: Codable, Identifiable, Equatable {
    let childId: String
    let guardianId: String
    let displayName: String
    let reminderTime: String
    let windowMinutes: Int
    let timezone: String

    var id: String { childId }

    enum CodingKeys: String, CodingKey {
        case childId = "child_id"
        case guardianId = "guardian_id"
        case displayName = "display_name"
        case reminderTime = "reminder_time"
        case windowMinutes = "window_minutes"
        case timezone
    }
}

struct MeResponse: Codable {
    let role: Role
    let guardianId: String?
    let child: ChildProfile?
    let children: [ChildProfile]

    enum CodingKeys: String, CodingKey {
        case role
        case guardianId = "guardian_id"
        case child
        case children
    }
}

struct ConfirmRequest: Codable {
    let childId: String

    enum CodingKeys: String, CodingKey {
        case childId = "child_id"
    }
}
