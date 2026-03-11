import enum


class ThreadStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    STALE = "stale"


class ProcessSignalType(str, enum.Enum):
    OPEN_LOOP = "open_loop"
    UNRESOLVED_THREAD = "unresolved_thread"
    MISSING_OWNER = "missing_owner"
    MISSING_DEADLINE = "missing_deadline"
    SLOW_MENTION_RESPONSE = "slow_mention_response"
    THEME_PATTERN = "theme_pattern"


class ProcessSignalSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessSignalStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    MUTED = "muted"


class ReportStatus(str, enum.Enum):
    ASSEMBLING = "assembling"
    AWAITING_VERIFICATION = "awaiting_verification"
    VERIFIED = "verified"
    REJECTED = "rejected"
    DELIVERED = "delivered"
    FAILED = "failed"


class ReportPeriodType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class LLMRunStage(str, enum.Enum):
    ANALYST = "analyst"
    VERIFIER = "verifier"
    FINALIZER = "finalizer"


class LLMRunStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

