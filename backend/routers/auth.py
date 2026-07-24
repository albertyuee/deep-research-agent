"""Authentication and first-phase user/department management APIs."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import (
    PERMISSIONS,
    User,
    _connect,
    _hash_password,
    authenticate,
    current_user,
    init_auth_db,
    require_permission,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=80)
    role: str = Field(default="researcher", pattern="^(admin|researcher|guest)$")
    department_id: str | None = None


class DepartmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    parent_id: str | None = None


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    role: str | None = Field(default=None, pattern="^(admin|researcher|guest)$")
    department_id: str | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


def _public_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "department_id": user.department_id,
        "permissions": sorted(PERMISSIONS.get(user.role, ())),
    }


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if not os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        return LoginResponse(success=True, data={"token": None, "user": _public_user(current_user())})
    result = authenticate(req.email, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    user, token = result
    return LoginResponse(success=True, data={"token": token, "user": _public_user(user)})


@router.get("/me", response_model=LoginResponse)
async def me(user: User = Depends(current_user)):
    return LoginResponse(success=True, data={"user": _public_user(user)})


@router.post("/users", response_model=LoginResponse)
async def create_user(req: CreateUserRequest, _: User = Depends(require_permission("user:manage"))):
    init_auth_db()
    try:
        with _connect() as conn:
            user_id = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO users (id,email,display_name,password_hash,role,department_id,created_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, req.email.strip().lower(), req.display_name.strip(), _hash_password(req.password), req.role, req.department_id, datetime.now(timezone.utc).isoformat()),
            )
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="邮箱已存在或部门不存在") from exc
    return LoginResponse(success=True, data={"user": _public_user(User(row["id"], row["email"], row["display_name"], row["role"], row["department_id"], bool(row["active"])))})


@router.get("/users", response_model=LoginResponse)
async def list_users(_: User = Depends(require_permission("user:manage"))):
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute("SELECT id,email,display_name,role,department_id,active FROM users ORDER BY created_at").fetchall()
    return LoginResponse(success=True, data={"users": [dict(row) for row in rows]})


@router.patch("/users/{user_id}", response_model=LoginResponse)
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: User = Depends(require_permission("user:manage")),
):
    init_auth_db()
    if user_id == admin.id and req.active is False:
        raise HTTPException(status_code=400, detail="不能禁用当前登录的管理员")
    updates: dict[str, object] = {}
    if req.display_name is not None:
        updates["display_name"] = req.display_name.strip()
    if req.role is not None:
        updates["role"] = req.role
    if "department_id" in req.model_fields_set:
        updates["department_id"] = req.department_id or None
    if req.active is not None:
        updates["active"] = int(req.active)
    if req.password:
        updates["password_hash"] = _hash_password(req.password)
    if not updates:
        raise HTTPException(status_code=400, detail="没有可更新的字段")

    assignments = ", ".join(f"{key}=?" for key in updates)
    values = [*updates.values(), user_id]
    with _connect() as conn:
        cursor = conn.execute(f"UPDATE users SET {assignments} WHERE id=?", values)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="用户不存在")
        row = conn.execute("SELECT id,email,display_name,role,department_id,active FROM users WHERE id=?", (user_id,)).fetchone()
    return LoginResponse(success=True, data={"user": dict(row)})


@router.delete("/users/{user_id}", response_model=LoginResponse)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_permission("user:manage")),
):
    init_auth_db()
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员")
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="用户不存在")
    return LoginResponse(success=True, data={"id": user_id, "message": "用户已删除"})


@router.post("/departments", response_model=LoginResponse)
async def create_department(req: DepartmentRequest, _: User = Depends(require_permission("user:manage"))):
    init_auth_db()
    department_id = uuid.uuid4().hex
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO departments (id,name,parent_id,created_at) VALUES (?,?,?,?)",
                (department_id, req.name.strip(), req.parent_id, datetime.now(timezone.utc).isoformat()),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="上级部门不存在") from exc
    return LoginResponse(success=True, data={"id": department_id, "name": req.name.strip(), "parent_id": req.parent_id})


@router.get("/departments", response_model=LoginResponse)
async def list_departments(user: User = Depends(current_user)):
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute("SELECT id,name,parent_id,created_at FROM departments ORDER BY name").fetchall()
    # 普通用户可以读取部门列表用于授权展示，不能修改。
    return LoginResponse(success=True, data={"departments": [dict(row) for row in rows], "current_department_id": user.department_id})
