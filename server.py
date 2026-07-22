#!/usr/bin/env python3
"""
MCP Server for Cerebro project management system.

Provides read-only access to Cerebro tasks, messages, and users
via the pycerebro library. Credentials are supplied through
CEREBRO_USER and CEREBRO_PASSWORD environment variables.
"""

import asyncio
import datetime
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, os.path.dirname(__file__))
from pycerebro import database, dbtypes, cclib


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MESSAGE_TYPE_NAMES = {
    dbtypes.MESSAGE_TYPE_DEFINITION: "Definition",
    dbtypes.MESSAGE_TYPE_REVIEW: "Review",
    dbtypes.MESSAGE_TYPE_REPORT: "Report",
    dbtypes.MESSAGE_TYPE_NOTE: "Note",
    dbtypes.MESSAGE_TYPE_CLIENT_REVIEW: "Client Review",
    dbtypes.MESSAGE_TYPE_RESOURCE_REPORT: "Resource Report",
    dbtypes.MESSAGE_TYPE_STATUS_CHANGES: "Status Change",
}

PRIORITY_NAMES = {
    dbtypes.TASK_PRIORITY_LOW: "Low",
    dbtypes.TASK_PRIORITY_BELOW_NORMAL: "Below Normal",
    dbtypes.TASK_PRIORITY_NORMAL: "Normal",
    dbtypes.TASK_PRIORITY_ABOVE_NORMAL: "Above Normal",
    dbtypes.TASK_PRIORITY_HIGHT: "High",
    dbtypes.TASK_PRIORITY_CRITICAL: "Critical",
}

# Days offset base: 01.01.2000
_CEREBRO_EPOCH = datetime.date(2000, 1, 1)

ATTACHMENT_TAG_NAMES = {
    dbtypes.ATTACHMENT_TAG_FILE: "File",
    dbtypes.ATTACHMENT_TAG_THUMB1: "Thumb1",
    dbtypes.ATTACHMENT_TAG_THUMB2: "Thumb2",
    dbtypes.ATTACHMENT_TAG_THUMB3: "Thumb3",
    dbtypes.ATTACHMENT_TAG_REVIEW: "Review",
    dbtypes.ATTACHMENT_TAG_LINK: "Link",
}

TAG_TYPE_NAMES = {
    dbtypes.TAG_TYPE_INTEGER: "Integer",
    dbtypes.TAG_TYPE_ENUM: "Enum",
    dbtypes.TAG_TYPE_FLOAT: "Float",
    dbtypes.TAG_TYPE_STRING: "String",
    dbtypes.TAG_TYPE_MULTI_ENUM: "MultiEnum",
    dbtypes.TAG_TYPE_USER: "User",
    dbtypes.TAG_TYPE_MULTI_USER: "MultiUser",
}


# ---------------------------------------------------------------------------
# Lifespan – single shared DB connection
# ---------------------------------------------------------------------------

@asynccontextmanager
async def app_lifespan(app):
    user = os.environ.get("CEREBRO_USER", "")
    password = os.environ.get("CEREBRO_PASSWORD", "")
    if not user or not password:
        raise RuntimeError("CEREBRO_USER and CEREBRO_PASSWORD environment variables must be set")

    db = database.Database()
    await asyncio.to_thread(db.connect, user, password)
    try:
        yield {"db": db}
    finally:
        await asyncio.to_thread(db.disconnect)


mcp = FastMCP("cerebro_mcp", lifespan=app_lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_to_date(days: Optional[float]) -> Optional[str]:
    """Convert Cerebro day-offset (float days from 2000-01-01) to ISO date string."""
    if days is None:
        return None
    try:
        d = _CEREBRO_EPOCH + datetime.timedelta(days=float(days))
        return d.isoformat()
    except Exception:
        return None


def _fmt_datetime(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return str(val)


def _task_to_dict(t: tuple) -> dict:
    return {
        "id": t[dbtypes.TASK_DATA_ID],
        "name": t[dbtypes.TASK_DATA_NAME],
        "path": t[dbtypes.TASK_DATA_PARENT_URL],
        "activity": t[dbtypes.TASK_DATA_ACTIVITY_NAME],
        "progress": t[dbtypes.TASK_DATA_PROGRESS],
        "priority": PRIORITY_NAMES.get(t[dbtypes.TASK_DATA_PRIORITY], str(t[dbtypes.TASK_DATA_PRIORITY])),
        "status_id": t[dbtypes.TASK_DATA_CC_STATUS],
        "planned_hours": t[dbtypes.TASK_DATA_PLANNED],
        "start": _days_to_date(t[dbtypes.TASK_DATA_HUMAN_START]),
        "finish": _days_to_date(t[dbtypes.TASK_DATA_HUMAN_FINISH]),
        "allocated": t[dbtypes.TASK_DATA_ALLOCATED],
        "created": _fmt_datetime(t[dbtypes.TASK_DATA_CREATED]),
        "modified": _fmt_datetime(t[dbtypes.TASK_DATA_MODIFIED]),
        "project_id": t[dbtypes.TASK_DATA_PROJECT_ID],
    }


def _message_to_dict(m: tuple) -> dict:
    return {
        "id": m[dbtypes.MESSAGE_DATA_ID],
        "task_id": m[dbtypes.MESSAGE_DATA_TID],
        "type": MESSAGE_TYPE_NAMES.get(m[dbtypes.MESSAGE_DATA_TYPE], str(m[dbtypes.MESSAGE_DATA_TYPE])),
        "author": m[dbtypes.MESSAGE_DATA_CREATOR_NAME],
        "created": _fmt_datetime(m[dbtypes.MESSAGE_DATA_CREATED]),
        "text": m[dbtypes.MESSAGE_DATA_TEXT],
        "work_time_min": m[dbtypes.MESSAGE_DATA_WORK_TIME],
        "approved_time_min": m[dbtypes.MESSAGE_DATA_APPROVED_TIME],
        "status_id": m[dbtypes.MESSAGE_DATA_STATUS_ID],
    }


def _user_to_dict(u: tuple) -> dict:
    is_resource = cclib.has_flag(u[dbtypes.USER_DATA_FLAGS], dbtypes.USER_FLAG_IS_RESOURCE)
    return {
        "id": u[dbtypes.USER_DATA_ID],
        "full_name": u[dbtypes.USER_DATA_FULL_NAME],
        "login": u[dbtypes.USER_DATA_LOGIN],
        "first_name": u[dbtypes.USER_DATA_FIRST_NAME],
        "last_name": u[dbtypes.USER_DATA_LAST_NAME],
        "email": u[dbtypes.USER_DATA_EMAIL],
        "phone": u[dbtypes.USER_DATA_PHONE],
        "is_resource": is_resource,
    }


def _status_to_dict(s: tuple) -> dict:
    return {
        "id": s[dbtypes.STATUS_DATA_ID],
        "name": s[dbtypes.STATUS_DATA_NAME],
        "description": s[dbtypes.STATUS_DATA_DESCRIPTION],
        "color": s[dbtypes.STATUS_DATA_COLOR],
        "order": s[dbtypes.STATUS_DATA_ORDER],
        "flags": s[dbtypes.STATUS_DATA_FLAGS],
    }


def _activity_to_dict(a: tuple) -> dict:
    return {
        "id": a[dbtypes.ACTIVITY_DATA_ID],
        "name": a[dbtypes.ACTIVITY_DATA_NAME],
        "color": a[dbtypes.ACTIVITY_DATA_COLOR],
    }


def _attachment_to_dict(a: tuple) -> dict:
    return {
        "id": a[dbtypes.ATTACHMENT_DATA_ID],
        "group_id": a[dbtypes.ATTACHMENT_DATA_GROUP_ID],
        "message_id": a[dbtypes.ATTACHMENT_DATA_EVENT_ID],
        "tag": ATTACHMENT_TAG_NAMES.get(a[dbtypes.ATTACHMENT_DATA_TAG], str(a[dbtypes.ATTACHMENT_DATA_TAG])),
        "file_name": a[dbtypes.ATTACHMENT_DATA_FILE_NAME],
        "file_size": a[dbtypes.ATTACHMENT_DATA_FILE_SIZE],
        "hash": a[dbtypes.ATTACHMENT_DATA_HASH],
        "comment": a[dbtypes.ATTACHMENT_DATA_COMMENT],
        "created": _fmt_datetime(a[dbtypes.ATTACHMENT_DATA_CREATED]),
    }


def _tag_to_dict(t: tuple) -> dict:
    return {
        "tag_id": t[dbtypes.TASK_TAG_DATA_TAG_ID],
        "name": t[dbtypes.TASK_TAG_DATA_NAME],
        "type": TAG_TYPE_NAMES.get(t[dbtypes.TASK_TAG_DATA_TYPE], str(t[dbtypes.TASK_TAG_DATA_TYPE])),
        "value": t[dbtypes.TASK_TAG_DATA_VALUE],
    }


def _check_item_to_dict(c: tuple) -> dict:
    return {
        "check_id": c[dbtypes.TASK_CHECK_DATA_CHECK_ID],
        "task_id": c[dbtypes.TASK_CHECK_DATA_TASK_ID],
        "value": c[dbtypes.TASK_CHECK_DATA_VALUE],
        "order": c[dbtypes.TASK_CHECK_DATA_ORDER],
    }


def _check_def_to_dict(c: tuple) -> dict:
    return {
        "id": c[dbtypes.CHECK_DATA_ID],
        "name": c[dbtypes.CHECK_DATA_NAME],
        "description": c[dbtypes.CHECK_DATA_DESCRIPTION],
    }


def _link_to_dict(l: tuple) -> dict:
    return {
        "id": l[dbtypes.TASK_LINK_ID],
        "src_task_id": l[dbtypes.TASK_LINK_SRC],
        "dst_task_id": l[dbtypes.TASK_LINK_DST],
        "flags": l[dbtypes.TASK_LINK_FLAGS],
    }


def _project_tag_to_dict(t: tuple) -> dict:
    return {
        "id": t[dbtypes.TAG_DATA_ID],
        "name": t[dbtypes.TAG_DATA_NAME],
        "type": TAG_TYPE_NAMES.get(t[dbtypes.TAG_DATA_TYPE], str(t[dbtypes.TAG_DATA_TYPE])),
        "project_id": t[dbtypes.TAG_DATA_PROJECT_ID],
    }


def _db(ctx: Context) -> database.Database:
    return ctx.request_context.lifespan_context["db"]


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class TaskIdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    task_id: int = Field(..., description="Cerebro task ID (integer)", gt=0)


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UrlInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    url: str = Field(..., description="Full task path, e.g. /Pipeline tools/Utilities/User Status/")


class UserTasksInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(..., description="Cerebro user ID (integer)", gt=0)
    include_done: bool = Field(False, description="Include tasks with progress=100%")


class MessageIdInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: int = Field(..., description="Cerebro message ID (integer)", gt=0)


class ProjectIdInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: int = Field(..., description="Cerebro project ID (integer)", gt=0)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="cerebro_get_root_tasks",
    annotations={
        "title": "Get Root Tasks (Projects)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_root_tasks(params: EmptyInput, ctx: Context) -> str:
    """Return the list of root-level tasks (top-level projects) from Cerebro.

    Each task includes id, name, path, activity, progress, priority, status_id,
    planned_hours, start/finish dates, allocated users, and project_id.

    Returns:
        str: JSON array of task objects. Each object has:
            - id (int): task ID
            - name (str): task name
            - path (str): parent path (e.g. "/")
            - activity (str): activity type name
            - progress (float): 0.0 – 100.0
            - priority (str): "Low" / "Normal" / "High" / etc.
            - status_id (int | null): current status ID
            - planned_hours (float | null): planned time in hours
            - start (str | null): ISO date
            - finish (str | null): ISO date
            - allocated (str): semicolon-separated user IDs
            - created (str | null): ISO datetime
            - modified (str | null): ISO datetime
            - project_id (int): project ID
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).root_tasks)
        tasks = [_task_to_dict(t) for t in (rows or [])]
        return json.dumps(tasks, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task",
    annotations={
        "title": "Get Task by ID",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task(params: TaskIdInput, ctx: Context) -> str:
    """Return full details of a single Cerebro task by its ID.

    Args:
        params (TaskIdInput):
            - task_id (int): Cerebro task ID (must be > 0)

    Returns:
        str: JSON object with task fields (same schema as cerebro_get_root_tasks),
             or an error string if the task is not found.
    """
    try:
        row = await asyncio.to_thread(_db(ctx).task, params.task_id)
        if row is None:
            return f"Error: Task {params.task_id} not found."
        return json.dumps(_task_to_dict(row), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_children",
    annotations={
        "title": "Get Subtasks of a Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_children(params: TaskIdInput, ctx: Context) -> str:
    """Return direct subtasks (children) of the specified task.

    Use this tool to traverse the task tree. Call with a root task's ID to get
    its top-level subtasks, then recurse as needed.

    Args:
        params (TaskIdInput):
            - task_id (int): Parent task ID

    Returns:
        str: JSON array of task objects (same schema as cerebro_get_root_tasks).
             Returns an empty array if the task has no children.
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).task_children, params.task_id)
        tasks = [_task_to_dict(t) for t in (rows or [])]
        return json.dumps(tasks, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_messages",
    annotations={
        "title": "Get Messages (Forum) of a Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_messages(params: TaskIdInput, ctx: Context) -> str:
    """Return all forum messages for a Cerebro task.

    Messages include task definitions, reviews, reports, notes, client reviews,
    resource reports, and status change events.

    Args:
        params (TaskIdInput):
            - task_id (int): Task ID

    Returns:
        str: JSON array of message objects. Each object has:
            - id (int): message ID
            - task_id (int): parent task ID
            - type (str): "Definition" / "Review" / "Report" / "Note" /
                          "Client Review" / "Resource Report" / "Status Change"
            - author (str): author display name
            - created (str | null): ISO datetime
            - text (str): message HTML text
            - work_time_min (float | null): reported work time in minutes
            - approved_time_min (float | null): approved time in minutes
            - status_id (int | null): status set by this message
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).task_messages, params.task_id)
        messages = [_message_to_dict(m) for m in (rows or [])]
        return json.dumps(messages, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_users",
    annotations={
        "title": "Get All Users",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_users(params: EmptyInput, ctx: Context) -> str:
    """Return all users and material resources registered in Cerebro.

    Args:
        params (EmptyInput): No parameters required.

    Returns:
        str: JSON array of user objects. Each object has:
            - id (int): user ID
            - full_name (str): display name
            - login (str): login name
            - first_name (str): first name
            - last_name (str): last name
            - email (str): email address
            - phone (str): phone number
            - is_resource (bool): true if this entry is a material resource,
                                  not a real user account
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).users)
        users = [_user_to_dict(u) for u in (rows or [])]
        return json.dumps(users, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Additional read-only tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="cerebro_get_task_by_url",
    annotations={
        "title": "Get Task by URL Path",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_by_url(params: UrlInput, ctx: Context) -> str:
    """Return a task by its full path URL, e.g. '/Pipeline tools/Utilities/User Status/'.

    This avoids manual tree traversal — use it when you know the full path.

    Args:
        params (UrlInput):
            - url (str): Full task path starting with '/'.

    Returns:
        str: JSON task object (same schema as cerebro_get_root_tasks),
             or an error string if not found.
    """
    try:
        # The DB function expects no trailing slash: /Foo/Bar not /Foo/Bar/
        url = params.url.rstrip("/")
        row = await asyncio.to_thread(_db(ctx).task_by_url, url)
        if row is None:
            return f"Error: Task not found for URL '{params.url}'"
        task_id = row[0]
        if not task_id:
            return f"Error: Task not found for URL '{params.url}'"
        # getTaskID_byURL may return text column — convert to int if needed
        if isinstance(task_id, str):
            try:
                task_id = int(task_id)
            except (ValueError, TypeError):
                return f"Error: Task not found for URL '{params.url}'"
        task_row = await asyncio.to_thread(_db(ctx).task, task_id)
        if task_row is None:
            return f"Error: Task not found for URL '{params.url}'"
        return json.dumps(_task_to_dict(task_row), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_statuses",
    annotations={
        "title": "Get All Statuses",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_statuses(params: EmptyInput, ctx: Context) -> str:
    """Return all task statuses defined in Cerebro.

    Use this to decode status_id values returned by task tools.

    Returns:
        str: JSON array of status objects. Each object has:
            - id (int): status ID
            - name (str): status name
            - description (str): status description
            - color (int): RGB color as integer
            - order (int): display order
            - flags (int): bitmask (bit 1 = inheritable, bit 2 = work started, bit 3 = work stopped)
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).statuses)
        return json.dumps([_status_to_dict(s) for s in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_activities",
    annotations={
        "title": "Get All Activities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_activities(params: EmptyInput, ctx: Context) -> str:
    """Return all activity types defined in Cerebro.

    Use this to decode activity names and IDs on tasks.

    Returns:
        str: JSON array of activity objects. Each object has:
            - id (int): activity ID
            - name (str): activity name
            - color (int): RGB color as integer
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).activities)
        return json.dumps([_activity_to_dict(a) for a in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_current_user",
    annotations={
        "title": "Get Current Logged-in User",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_current_user(params: EmptyInput, ctx: Context) -> str:
    """Return the user account currently authenticated with Cerebro.

    Returns:
        str: JSON user object (same schema as cerebro_get_users items).
    """
    try:
        row = await asyncio.to_thread(_db(ctx).current_user)
        return json.dumps(_user_to_dict(row), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_user_tasks",
    annotations={
        "title": "Get Tasks Assigned to a User",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_user_tasks(params: UserTasksInput, ctx: Context) -> str:
    """Return all tasks allocated to a specific user.

    Args:
        params (UserTasksInput):
            - user_id (int): Cerebro user ID
            - include_done (bool): if true, includes tasks with progress=100% (default false)

    Returns:
        str: JSON array of task objects (same schema as cerebro_get_root_tasks).
             Returns an empty array if the user has no assigned tasks.
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).to_do_task_list, params.user_id, params.include_done)
        tasks = [_task_to_dict(t) for t in (rows or [])]
        return json.dumps(tasks, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_tags",
    annotations={
        "title": "Get Custom Tags of a Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_tags(params: TaskIdInput, ctx: Context) -> str:
    """Return custom tag values set on a task.

    Tags are project-defined metadata fields (integers, floats, strings, enums, user refs).
    Use cerebro_get_project_tags to see available tags for a project.

    Args:
        params (TaskIdInput):
            - task_id (int): Task ID

    Returns:
        str: JSON array of tag objects. Each object has:
            - tag_id (int): tag schema ID
            - name (str): tag name
            - type (str): "Integer" / "Float" / "String" / "Enum" / "MultiEnum" / "User" / "MultiUser"
            - value (str | null): tag value; multiple values separated by semicolons
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).task_tags, params.task_id)
        return json.dumps([_tag_to_dict(t) for t in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_attachments",
    annotations={
        "title": "Get Attachments of a Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_attachments(params: TaskIdInput, ctx: Context) -> str:
    """Return files attached to a task across all its messages.

    Each physical file may appear as 1-5 records sharing the same group_id:
    one for the file itself (tag=File) and optionally thumbnail records (Thumb1/2/3)
    and a review file (Review). Links appear as a single record with tag=Link.

    Args:
        params (TaskIdInput):
            - task_id (int): Task ID

    Returns:
        str: JSON array of attachment records. Each record has:
            - id (int): attachment record ID
            - group_id (int): groups related records for one attachment
            - message_id (int): message the attachment belongs to
            - tag (str): "File" / "Link" / "Thumb1" / "Thumb2" / "Thumb3" / "Review"
            - file_name (str): file name (for links: full path)
            - file_size (int): bytes (0 for links)
            - hash (str | null): file hash on Cargador storage
            - comment (str): attachment comment
            - created (str | null): ISO datetime
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).task_attachments, params.task_id)
        return json.dumps([_attachment_to_dict(a) for a in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_message_attachments",
    annotations={
        "title": "Get Attachments of a Message",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_message_attachments(params: MessageIdInput, ctx: Context) -> str:
    """Return files attached to a specific forum message.

    Args:
        params (MessageIdInput):
            - message_id (int): Message ID

    Returns:
        str: JSON array of attachment records (same schema as cerebro_get_task_attachments).
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).message_attachments, params.message_id)
        return json.dumps([_attachment_to_dict(a) for a in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_checks",
    annotations={
        "title": "Get Checklist of a Task",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_checks(params: TaskIdInput, ctx: Context) -> str:
    """Return checklist items assigned to a task.

    check_id references a check definition from cerebro_get_checks (which has the name).

    Args:
        params (TaskIdInput):
            - task_id (int): Task ID

    Returns:
        str: JSON array of checklist items. Each item has:
            - check_id (int): references the check definition (see cerebro_get_checks)
            - task_id (int): task this item belongs to
            - value (int): 0 = unchecked, 1 = checked
            - order (int): display order
    """
    try:
        # Workaround: pycerebro's task_checks() passes to_array(task_id) with ?::bigint
        # (scalar cast) which fails. The actual DB function takes bigint[].
        rows = await asyncio.to_thread(
            _db(ctx).execute,
            'select * from "taskChecksColumn"(?::bigint[])',
            [params.task_id],
        )
        return json.dumps([_check_item_to_dict(c) for c in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_checks",
    annotations={
        "title": "Get All Check Definitions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_checks(params: EmptyInput, ctx: Context) -> str:
    """Return all check (checklist item) definitions in Cerebro.

    Use this alongside cerebro_get_task_checks to resolve check names from check_id values.

    Returns:
        str: JSON array of check objects. Each object has:
            - id (int): check ID
            - name (str): check name
            - description (str): check description
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).checks)
        return json.dumps([_check_def_to_dict(c) for c in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_task_links",
    annotations={
        "title": "Get Task Dependencies",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_task_links(params: TaskIdInput, ctx: Context) -> str:
    """Return sequential dependency links for a task (predecessor/follower relationships).

    Args:
        params (TaskIdInput):
            - task_id (int): Task ID

    Returns:
        str: JSON array of link objects. Each object has:
            - id (int): link ID
            - src_task_id (int): predecessor task ID
            - dst_task_id (int): follower task ID
            - flags (int): link flags
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).task_links, params.task_id)
        return json.dumps([_link_to_dict(l) for l in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="cerebro_get_project_tags",
    annotations={
        "title": "Get Tag Schema of a Project",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cerebro_get_project_tags(params: ProjectIdInput, ctx: Context) -> str:
    """Return the tag schema for a project — all custom tag fields available on its tasks.

    The project_id is returned by task tools as the 'project_id' field.

    Args:
        params (ProjectIdInput):
            - project_id (int): Project ID

    Returns:
        str: JSON array of tag schema objects. Each object has:
            - id (int): tag ID
            - name (str): tag name
            - type (str): "Integer" / "Float" / "String" / "Enum" / "MultiEnum" / "User" / "MultiUser"
            - project_id (int): project this tag belongs to
    """
    try:
        rows = await asyncio.to_thread(_db(ctx).project_tags, params.project_id)
        return json.dumps([_project_tag_to_dict(t) for t in (rows or [])], ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
