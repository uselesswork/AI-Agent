"""投递截止日期、面试日程、站内提醒和已确认材料的面试准备。"""

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api import applications
from app.models.planning import (
    InterviewPreparation, MilestoneCreate, MilestoneDetail, MilestoneUpdate, ReminderList,
)
from app.services.application_repository import ApplicationNotFoundError
from app.services.interview_preparation import compose_interview_preparation
from app.services.planning_repository import MilestoneNotFoundError, PlanningRepository

router = APIRouter(prefix="/api/planning", tags=["日程与面试准备"])


def get_planning_repository() -> PlanningRepository:
    return PlanningRepository(applications.get_repository().engine)


@router.get("/reminders", response_model=ReminderList)
def list_reminders(days: int = Query(default=7, ge=0, le=30)) -> ReminderList:
    return get_planning_repository().reminders(days)


@router.post("/applications/{record_id}/milestones", response_model=MilestoneDetail,
             status_code=status.HTTP_201_CREATED)
def create_milestone(record_id: int, data: MilestoneCreate) -> MilestoneDetail:
    try:
        return get_planning_repository().create(record_id, data)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.get("/applications/{record_id}/milestones", response_model=list[MilestoneDetail])
def list_milestones(record_id: int) -> list[MilestoneDetail]:
    try:
        return get_planning_repository().list(record_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="投递记录不存在。") from exc


@router.patch("/applications/{record_id}/milestones/{milestone_id}",
              response_model=MilestoneDetail)
def update_milestone(record_id: int, milestone_id: int,
                     data: MilestoneUpdate) -> MilestoneDetail:
    try:
        return get_planning_repository().update(record_id, milestone_id, data)
    except MilestoneNotFoundError as exc:
        raise HTTPException(status_code=404, detail="日程不存在或不属于该投递。") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/applications/{record_id}/milestones/{milestone_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(record_id: int, milestone_id: int) -> Response:
    try:
        get_planning_repository().delete(record_id, milestone_id)
    except MilestoneNotFoundError as exc:
        raise HTTPException(status_code=404, detail="日程不存在或不属于该投递。") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/applications/{record_id}/interview-prep",
            response_model=InterviewPreparation)
def get_interview_preparation(
    record_id: int, response: Response, version: int = Query(ge=1),
) -> InterviewPreparation:
    response.headers["Cache-Control"] = "no-store"
    record = applications.get_application(record_id)
    saved = applications.get_draft_version(record_id, version)
    try:
        return compose_interview_preparation(record, saved)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
