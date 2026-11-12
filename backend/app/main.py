"""FastAPI app. Run with:  uvicorn app.main:create_app --factory --reload"""
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import (
    AdultConfirmRequest,
    ChildCreateRequest,
    ChildCreatedResponse,
    DeviceTokenResponse,
    GuardianCreateRequest,
    GuardianCreatedResponse,
    MeResponse,
    NotificationEvent,
    ReminderStateResponse,
    Role,
)
from .notification import NotificationGateway
from .reminder_engine import Clock, NotFoundError, Principal, ReminderEngine, utc_now
from .store import Store

DEFAULT_DB_PATH = "med_reminder.db"


def create_app(db_path: str | None = None, clock: Clock = utc_now) -> FastAPI:
    store = Store(db_path or os.environ.get("MED_REMINDER_DB", DEFAULT_DB_PATH))
    engine = ReminderEngine(store, NotificationGateway(store), clock)
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(title="Medication Reminder Backend", version="0.2.0")
    app.state.engine = engine

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
        found = engine.authenticate(credentials.credentials) if credentials else None
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return found

    def require_child(who: Principal = Depends(principal)) -> Principal:
        if who.role != Role.child:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child device token required")
        return who

    def require_guardian(who: Principal = Depends(principal)) -> Principal:
        if who.role != Role.guardian:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guardian token required")
        return who

    def not_found(error: NotFoundError) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Open sign-up: a guardian can only ever see and control children they created.
    @app.post("/guardians", response_model=GuardianCreatedResponse, status_code=status.HTTP_201_CREATED)
    def create_guardian(payload: GuardianCreateRequest) -> GuardianCreatedResponse:
        guardian_id, token = engine.create_guardian(payload.display_name)
        return GuardianCreatedResponse(guardian_id=guardian_id, display_name=payload.display_name, token=token)

    @app.get("/me", response_model=MeResponse)
    def me(who: Principal = Depends(principal)) -> MeResponse:
        if who.role == Role.child:
            child = engine.get_child(who.subject_id)
            return MeResponse(role=Role.child, guardian_id=child.guardian_id, child=child)
        return MeResponse(role=Role.guardian, guardian_id=who.subject_id,
                          children=engine.list_children(who.subject_id))

    @app.post("/children", response_model=ChildCreatedResponse, status_code=status.HTTP_201_CREATED)
    def create_child(payload: ChildCreateRequest, who: Principal = Depends(require_guardian)) -> ChildCreatedResponse:
        child, token = engine.create_child(who.subject_id, payload)
        return ChildCreatedResponse(child=child, device_token=token)

    @app.post("/children/{child_id}/device-token", response_model=DeviceTokenResponse)
    def reissue_device_token(child_id: str, who: Principal = Depends(require_guardian)) -> DeviceTokenResponse:
        try:
            return DeviceTokenResponse(device_token=engine.reissue_child_token(who.subject_id, child_id))
        except NotFoundError as error:
            raise not_found(error) from error

    @app.get("/reminders/state", response_model=ReminderStateResponse)
    def child_state(who: Principal = Depends(require_child)) -> ReminderStateResponse:
        return engine.current_state(who.subject_id)

    @app.get("/reminders/state/{child_id}", response_model=ReminderStateResponse)
    def guardian_state(child_id: str, who: Principal = Depends(require_guardian)) -> ReminderStateResponse:
        try:
            engine.get_owned_child(who.subject_id, child_id)
        except NotFoundError as error:
            raise not_found(error) from error
        return engine.current_state(child_id)

    @app.post("/reminders/mark-taken", response_model=ReminderStateResponse)
    def mark_taken(who: Principal = Depends(require_child)) -> ReminderStateResponse:
        return engine.mark_taken_by_child(who.subject_id)

    @app.post("/reminders/confirm", response_model=ReminderStateResponse)
    def confirm(payload: AdultConfirmRequest, who: Principal = Depends(require_guardian)) -> ReminderStateResponse:
        try:
            return engine.confirm_by_adult(who.subject_id, payload.child_id)
        except NotFoundError as error:
            raise not_found(error) from error

    @app.get("/notifications", response_model=list[NotificationEvent])
    def notifications(who: Principal = Depends(require_guardian)) -> list[NotificationEvent]:
        return engine.list_notifications(who.subject_id)

    return app
