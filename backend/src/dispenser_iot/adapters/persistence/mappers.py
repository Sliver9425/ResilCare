from uuid import uuid4

from src.dispenser_iot.adapters.persistence.models import (
    CompartmentModel, DispenseRecordModel, DispenserModel,
)
from src.dispenser_iot.domain.aggregates import Compartment, DispenserIoT, DispenseRecord
from src.dispenser_iot.domain.value_objects import (
    ConnectivityState, ConnectivityStatus, DispenseOrigin, DispenseOutcome, DispenseRecordId,
    DispenserId, PatientId, PowerSource, PowerStatus, PrescriptionItemId, SerialNumber,
    SlotNumber, StockLevel,
)


def record_to_domain(r: DispenseRecordModel) -> DispenseRecord:
    return DispenseRecord(
        id=DispenseRecordId(r.id), event_id=r.event_id, slot=SlotNumber(r.slot),
        scheduled_at=r.scheduled_at, dispensed_at=r.dispensed_at,
        outcome=DispenseOutcome(r.outcome), origin=DispenseOrigin(r.origin),
    )


def to_domain(m: DispenserModel, records: list[DispenseRecordModel]) -> DispenserIoT:
    return DispenserIoT(
        id=DispenserId(m.id), owner_id=PatientId(m.owner_id),
        serial_number=SerialNumber(m.serial_number),
        connectivity=ConnectivityState(ConnectivityStatus(m.connectivity_status), m.last_seen_at),
        power=PowerStatus(PowerSource(m.power_source), m.battery_pct),
        compartments=[
            Compartment(
                slot=SlotNumber(c.slot),
                item_ref=PrescriptionItemId(c.prescription_item_id) if c.prescription_item_id else None,
                stock=StockLevel(c.stock_remaining, c.low_threshold),
            )
            for c in m.compartments
        ],
        recent_records=[record_to_domain(r) for r in records],
        version=m.version,
    )


def apply_to_model(d: DispenserIoT, m: DispenserModel) -> None:
    m.owner_id = d.owner_id.value
    m.serial_number = d.serial_number.value
    m.connectivity_status = d.connectivity.status.value
    m.last_seen_at = d.connectivity.last_seen
    m.power_source = d.power.source.value
    m.battery_pct = d.power.battery_pct

    existing = {c.slot: c for c in m.compartments}
    synced: list[CompartmentModel] = []
    for c in d.compartments:
        cm = existing.get(c.slot.value) or CompartmentModel(id=uuid4(), slot=c.slot.value)
        cm.prescription_item_id = c.item_ref.value if c.item_ref else None
        cm.stock_remaining = c.stock.remaining
        cm.low_threshold = c.stock.low_threshold
        synced.append(cm)
    m.compartments = synced