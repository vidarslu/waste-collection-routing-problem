from dataclasses import dataclass


@dataclass(frozen=True)
class Vehicle:
    id: str
    capacity: int
    max_shift: int
    startup_cost: int = 0


@dataclass(frozen=True)
class Customer:
    id: str
    demand: int
    service: int
    lat: float
    lon: float


@dataclass(frozen=True)
class Depot:
    id: str
    lat: float
    lon: float


@dataclass(frozen=True)
class DisposalFacility:
    id: str
    lat: float
    lon: float
