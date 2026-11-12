from datetime import datetime, time
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


class ReminderStatus(str, Enum):
    pending = "pending"
    child_marked_taken = "child_marked_taken"
    adult_confirmed = "adult_confirmed"


class Role(str, Enum):
    guardian = "guardian"
    child = "child"


class GuardianCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)


class GuardianCreatedResponse(BaseModel):
    guardian_id: str
    display_name: str
    token: str = Field(..., description="Bearer token for the guardian's device. Shown once.")


class ChildCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    reminder_time: time = Field(..., description="Local time the medication window opens.")
    window_minutes: int = Field(60, ge=15, le=720, description="Length of the window (DeviceActivity minimum is 15).")
    timezone: str = Field(..., description="IANA timezone of the child's device, e.g. America/New_York.")

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"Unknown IANA timezone '{value}'") from error
        return value

    @model_validator(mode="after")
    def _window_within_day(self) -> "ChildCreateRequest":
        start_minutes = self.reminder_time.hour * 60 + self.reminder_time.minute
        if start_minutes + self.window_minutes > 24 * 60:
            raise ValueError("The medication window must end before midnight.")
        return self


class ChildProfile(BaseModel):
    child_id: str
    guardian_id: str
    display_name: str
    reminder_time: time
    window_minutes: int
    timezone: str


class ChildCreatedResponse(BaseModel):
    child: ChildProfile
    device_token: str = Field(..., description="Pairing code for the child's device. Shown once.")


class DeviceTokenResponse(BaseModel):
    device_token: str


class MeResponse(BaseModel):
    role: Role
    guardian_id: str | None = None
    child: ChildProfile | None = None
    children: list[ChildProfile] = Field(default_factory=list)


class AdultConfirmRequest(BaseModel):
    child_id: str = Field(..., min_length=1)


class ReminderStateResponse(BaseModel):
    child_id: str
    date_key: str
    status: ReminderStatus
    screen_time_should_be_restricted: bool
    reminder_starts_at: datetime
    child_marked_at: datetime | None
    adult_confirmed_at: datetime | None


class NotificationEvent(BaseModel):
    guardian_id: str
    child_id: str
    date_key: str
    title: str
    body: str
    created_at: datetime
