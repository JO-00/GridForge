from __future__ import annotations

from pydantic import BaseModel, field_validator , Field
from typing import Literal


class MacroElement(BaseModel):
    id : str
    @field_validator("id")
    def validate_id(cls, id : str):
        if id.startswith("macro_"):
            return id
        raise ValueError(f"invalid id = {id} for macro node")


class CircuitBreaker(MacroElement):
    rated_current_ka: float
    voltage_level_kv: float
    breaker_type: str

    @field_validator("breaker_type")
    def validate_breaker_type(cls, breaker_type: str):
        if breaker_type in ("air", "oil", "sf6", "vacuum"):
            return breaker_type
        raise ValueError(f"invalid breaker_type = {breaker_type}")


class MacroGraph(BaseModel):
    nodes: list[MacroElement] = []
    edges: list[tuple[str, str]] = []
    gateways: list[CircuitBreaker] = [] #to the external main grid

    @classmethod
    def merge_macrographs(cls, graphs: list[MacroGraph]) -> MacroGraph:
        merged_nodes: list[MacroElement] = []
        merged_edges: list[tuple[str, str]] = []
        seen_node_ids: set[str] = set()
        seen_edges: set[tuple[str, str]] = set()

        for g in graphs:
            for node in g.nodes:
                if node.id not in seen_node_ids:
                    seen_node_ids.add(node.id)
                    merged_nodes.append(node)
            for edge in g.edges:
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    merged_edges.append(edge)

        return cls(nodes=merged_nodes, edges=merged_edges)

            





            





class Generator(MacroElement):
    rated_power_mw : float
    voltage_level_kv : float
    generator_type : Literal[
        "thermal", "hydro", "solar", "wind", "gas", "nuclear"
    ]




class Storage(MacroElement):
    rated_power_mw : float
    energy_capacity_mwh : float
    nominal_voltage_kv : float
    storage_type : Literal[
        "battery", "pumped_hydro"
    ]

class Transformer(MacroElement):
    primary_voltage_kv    : float 
    secondary_voltage_kv : float
    rated_power_mva : float
    transformer_type : str

    @field_validator("transformer_type")
    def validate(cls, transformer_type):
        if transformer_type in ("step-up","step-down"):
            return transformer_type
        raise ValueError(f"invalid transformer_type = {transformer_type}")


class Substation(MacroElement):
    voltage_levels_kv : list[float]
    substation_type : str
    @field_validator("substation_type")
    def validate(cls, substation_type):
        if substation_type in ("transmission","distribution","switching"):
            return substation_type
        raise ValueError(f"invalid substation_type = {substation_type}")





class Load(MacroElement):
    consumer_type : str
    rated_demand_mw : float
    nominal_voltage_kv : float
    priority : int

    @field_validator("priority")
    def validate_priority(cls, priority):
        if 0<= priority<=10:
            return priority
        raise ValueError(f"invalid priority = {priority}")

    @field_validator("consumer_type")
    def validate_consumer_type(cls, consumer_type):
        return consumer_type # for now


class Bus(MacroElement):
    voltage_level_kv: float




        






