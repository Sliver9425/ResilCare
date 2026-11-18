import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin


class DispenserModel(Base, TimestampMixin):
    __tablename__ = "dispensers"
    __table_args__ = (
        CheckConstraint("connectivity_status IN ('ONLINE','OFFLINE')", name="connectivity"),
        CheckConstraint("power_source IN ('MAINS','BATTERY')", name="power_source"),
        CheckConstraint("battery_pct BETWEEN 0 AND 100", name="battery_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)  # PatientId (sin FK física)
    serial_number: Mapped[str] = mapped_column(String(64), unique=True)
    connectivity_status: Mapped[str] = mapped_column(String(8), default="OFFLINE")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    power_source: Mapped[str] = mapped_column(String(8), default="MAINS")
    battery_pct: Mapped[int] = mapped_column(SmallInteger, default=100)
    version: Mapped[int] = mapped_column(Integer, default=1)

    compartments: Mapped[list["CompartmentModel"]] = relationship(
        back_populates="dispenser", cascade="all, delete-orphan", lazy="selectin"
    )

    __mapper_args__ = {"version_id_col": version}


class CompartmentModel(Base):
    __tablename__ = "compartments"
    __table_args__ = (
        UniqueConstraint("dispenser_id", "slot", name="slot"),
        UniqueConstraint("dispenser_id", "prescription_item_id", name="item"),  # 1 slot ↔ 1 ítem
        CheckConstraint("stock_remaining >= 0", name="stock_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    dispenser_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dispensers.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[int] = mapped_column(SmallInteger)
    prescription_item_id: Mapped[uuid.UUID | None] = mapped_column()  # ref externa
    stock_remaining: Mapped[int] = mapped_column(Integer, default=0)
    low_threshold: Mapped[int] = mapped_column(Integer, default=3)

    dispenser: Mapped[DispenserModel] = relationship(back_populates="compartments")


class DispenseRecordModel(Base):
    """Sin relationship en el agregado: se consulta como ventana acotada (decisión Fase 1 #2)."""
    __tablename__ = "dispense_records"
    __table_args__ = (
        CheckConstraint("outcome IN ('DISPENSED','MISSED','JAMMED','REFUSED')", name="outcome"),
        CheckConstraint("origin IN ('ONLINE','OFFLINE_SYNCED')", name="origin"),
        Index("ix_dispense_records_dispenser_scheduled", "dispenser_id", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(unique=True)  # idempotencia a nivel de dato
    dispenser_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dispensers.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(SmallInteger)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dispensed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(16))
    origin: Mapped[str] = mapped_column(String(16))