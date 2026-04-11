"""SQLAlchemy ORM models for Postgres-backed aggregates."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base


class WorkspaceModel(Base):
    """Workspace persistence model."""

    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    projects: Mapped[list[ProjectModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class ProjectModel(Base):
    """Project persistence model."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="projects")
    tasks: Mapped[list[TaskModel]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class TaskModel(Base):
    """Task persistence model."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="todo")
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    assigned_to: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    project: Mapped[ProjectModel] = relationship(back_populates="tasks")
    events: Mapped[list[TaskEventModel]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskEventModel(Base):
    """Task audit-event persistence model."""

    __tablename__ = "task_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column("type", String(64))
    payload: Mapped[dict[str, str]] = mapped_column(JSON())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    task: Mapped[TaskModel] = relationship(back_populates="events")
