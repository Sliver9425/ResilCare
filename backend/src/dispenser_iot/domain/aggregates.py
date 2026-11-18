from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable
from uuid import UUID

from src.dispenser_iot.domain.events import (
    DispenseRequested, DispenserCameOnline, DispenserWentOffline, DoseDispensed, DoseMissed,
    PowerOutageDetected, PowerRestored, StockLow,
)
from src.dispenser_iot.domain.value_objects import (
    MAX_SLOTS, ConnectivityState, ConnectivityStatus as CS, DispenseOrigin, DispenseOutcome,
    DispenseRecordId, DispenserId, PatientId, PowerSource, PowerStatus, PrescriptionItemId,
    SerialNumber, SlotNumber, StockLevel,
)
from src.shared_kernel.domain import AggregateRoot, InvariantViolation


@dataclass(slots=True)
class Compartment:
    slot: SlotNumber
    item_ref: PrescriptionItemId | None = None
    stock: StockLevel = field(default_factory=lambda: StockLevel(0))


@dataclass(frozen=True, slots=True)
class DispenseRecord:
    id: DispenseRecordId
    event_id: UUID
    slot: SlotNumber
    scheduled_at: datetime
    dispensed_at: datetime | None
    outcome: DispenseOutcome
    origin: DispenseOrigin


class DispenserIoT(AggregateRoot):
    LOG_WINDOW = 50  # decisión Fase 1 #2: ventana acotada dentro del agregado

    def __init__(
        self, *, id: DispenserId, owner_id: PatientId, serial_number: SerialNumber,
        connectivity: ConnectivityState, power: PowerStatus,
        compartments: Iterable[Compartment], recent_records: Iterable[DispenseRecord] = (),
        version: int = 0,
    ) -> None:
        super().__init__()
        self.id, self.owner_id, self.serial_number = id, owner_id, serial_number
        self.connectivity, self.power = connectivity, power
        self._compartments = {c.slot.value: c for c in compartments}
        if not self._compartments:
            raise InvariantViolation("Un dispensador necesita al menos un compartimento")
        self._log: list[DispenseRecord] = list(recent_records)
        self._new_records: list[DispenseRecord] = []
        self.version = version

    @classmethod
    def register(cls, *, owner_id: PatientId, serial_number: SerialNumber, slot_count: int) -> DispenserIoT:
        if not 1 <= slot_count <= MAX_SLOTS:
            raise InvariantViolation(f"slot_count debe estar entre 1 y {MAX_SLOTS}")
        return cls(
            id=DispenserId.new(), owner_id=owner_id, serial_number=serial_number,
            connectivity=ConnectivityState(CS.OFFLINE, None),
            power=PowerStatus(PowerSource.MAINS, 100),
            compartments=[Compartment(SlotNumber(i)) for i in range(1, slot_count + 1)],
        )

    @property
    def compartments(self) -> tuple[Compartment, ...]:
        return tuple(self._compartments[k] for k in sorted(self._compartments))

    @property
    def recent_records(self) -> tuple[DispenseRecord, ...]:
        return tuple(self._log)

    def pull_new_records(self) -> list[DispenseRecord]:
        new, self._new_records = self._new_records, []
        return new

    # ---- conectividad ----
    def mark_online(self, at: datetime) -> bool:
        came_online = self.connectivity.status is CS.OFFLINE
        last = max(at, self.connectivity.last_seen) if self.connectivity.last_seen else at
        self.connectivity = ConnectivityState(CS.ONLINE, last)
        if came_online:
            self._record(DispenserCameOnline(dispenser_id=self.id, owner_id=self.owner_id, occurred_at=at))
        return came_online

    def register_heartbeat(self, at: datetime) -> bool:
        return self.mark_online(at)  # un pulso implica que está vivo

    def mark_offline(self, at: datetime) -> bool:
        if self.connectivity.status is CS.OFFLINE:
            return False
        self.connectivity = ConnectivityState(CS.OFFLINE, self.connectivity.last_seen)
        self._record(DispenserWentOffline(dispenser_id=self.id, owner_id=self.owner_id, occurred_at=at))
        return True

    # ---- energía ----
    def update_power(self, source: PowerSource, battery_pct: int, at: datetime) -> None:
        prev = self.power
        self.power = PowerStatus(source, battery_pct)
        kw = dict(dispenser_id=self.id, owner_id=self.owner_id, occurred_at=at, battery_pct=battery_pct)
        if prev.source is PowerSource.MAINS and source is PowerSource.BATTERY:
            self._record(PowerOutageDetected(**kw))
        elif prev.source is PowerSource.BATTERY and source is PowerSource.MAINS:
            self._record(PowerRestored(**kw))

    def report_power_outage(self, battery_pct: int, at: datetime) -> None:
        self.update_power(PowerSource.BATTERY, battery_pct, at)

    # ---- compartimentos ----
    def load_compartment(
        self, slot: SlotNumber, item: PrescriptionItemId, stock: int, low_threshold: int = 3,
    ) -> None:
        comp = self._compartment(slot)
        if any(o.item_ref == item for o in self._compartments.values() if o.slot != slot):
            raise InvariantViolation("Ese ítem de receta ya está cargado en otro compartimento")
        if comp.item_ref is not None and comp.item_ref != item and not comp.stock.is_empty:
            raise InvariantViolation("El compartimento contiene otro medicamento con stock")
        base = comp.stock if comp.item_ref == item else StockLevel(0)
        comp.stock = StockLevel(base.add(stock).remaining, low_threshold)
        comp.item_ref = item

    # ---- dispensación ----
    def request_dispense(self, slot: SlotNumber) -> None:
        if self.connectivity.status is CS.OFFLINE:
            raise InvariantViolation("Dispositivo offline: el comando manual no puede entregarse")
        comp = self._compartment(slot)
        if comp.item_ref is None or comp.stock.is_empty:
            raise InvariantViolation("No se puede dispensar de un compartimento vacío")
        self._record(DispenseRequested(dispenser_id=self.id, owner_id=self.owner_id, slot=slot))

    def confirm_dispense(
        self, *, event_id: UUID, slot: SlotNumber, scheduled_at: datetime,
        dispensed_at: datetime | None, outcome: DispenseOutcome, origin: DispenseOrigin,
    ) -> bool:
        """False si el evento ya estaba en la ventana (duplicado QoS 1)."""
        if any(r.event_id == event_id for r in self._log):
            return False
        comp = self._compartment(slot)
        rec = DispenseRecord(DispenseRecordId.new(), event_id, slot, scheduled_at,
                             dispensed_at, outcome, origin)
        self._log.append(rec)
        self._log.sort(key=lambda r: r.scheduled_at, reverse=True)
        del self._log[self.LOG_WINDOW:]
        self._new_records.append(rec)

        base = dict(dispenser_id=self.id, owner_id=self.owner_id, slot=slot)
        if outcome is DispenseOutcome.DISPENSED:
            was_low = comp.stock.is_low
            comp.stock = comp.stock.consume()
            self._record(DoseDispensed(
                **base, prescription_item_id=comp.item_ref, scheduled_at=scheduled_at,
                dispensed_at=dispensed_at, origin=origin,
                occurred_at=dispensed_at or scheduled_at,
            ))
            if comp.stock.is_low and not was_low:
                self._record(StockLow(**base, remaining=comp.stock.remaining))
        elif outcome is DispenseOutcome.MISSED:
            self._record(DoseMissed(**base, scheduled_at=scheduled_at, occurred_at=scheduled_at))
        return True

    def _compartment(self, slot: SlotNumber) -> Compartment:
        try:
            return self._compartments[slot.value]
        except KeyError:
            raise InvariantViolation(f"El slot {slot.value} no existe en este dispensador") from None