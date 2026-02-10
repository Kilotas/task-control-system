from pydantic import BaseModel


class AggregateAsyncIn(BaseModel):
    unique_codes: list[str]
    user_id: int | None = None


class TaskStartedOut(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusOut(BaseModel):
    task_id: str
    status: str
    result: dict | None
