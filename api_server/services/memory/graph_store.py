import json
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

class RelationshipType(Enum):
    RELATED_TO = "related_to"
    CAUSED_BY = "caused_by"
    PART_OF = "part_of"
    SIMILAR_TO = "similar_to"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"

@dataclass
class MemoryNode:
    id: str
    memory_id: str
    entity_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

@dataclass
class MemoryEdge:
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class MemoryGraphStore:
    def __init__(self, persist_path: Optional[str] = None):
        if persist_path is None:
            persist_path = os.path.join(
                os.path.expanduser("~"),
                ".cato",
                "memory_graph.json",
            )
        self._persist_path = persist_path
        self._nodes: Dict[str, MemoryNode] = {}
        self._edges: Dict[str, MemoryEdge] = {}
        self._adjacency: Dict[str, Set[str]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, "r") as f:
                    data = json.load(f)
                    self._nodes = {
                        k: MemoryNode(**v) 
                        for k, v in data.get("nodes", {}).items()
                    }
                    self._edges = {
                        k: MemoryEdge(**v) 
                        for k, v in data.get("edges", {}).items()
                    }
                    self._adjacency = {
                        k: set(v) 
                        for k, v in data.get("adjacency", {}).items()
                    }
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
        data = {
            "nodes": {k: vars(v) for k, v in self._nodes.items()},
            "edges": {k: vars(v) for k, v in self._edges.items()},
            "adjacency": {k: list(v) for k, v in self._adjacency.items()},
        }
        with open(self._persist_path, "w") as f:
            json.dump(data, f)

    def add_node(self, node: MemoryNode) -> bool:
        if node.id in self._nodes:
            return False
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = set()
        self._save()
        return True

    def add_edge(self, edge: MemoryEdge) -> bool:
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            return False
        if edge.id in self._edges:
            return False
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        self._adjacency.setdefault(edge.target_id, set()).add(edge.source_id)
        self._save()
        return True

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        return self._nodes.get(node_id)

    def get_neighbors(
        self,
        node_id: str,
        relationship: Optional[str] = None,
    ) -> List[MemoryNode]:
        if node_id not in self._adjacency:
            return []
        
        neighbors = []
        for neighbor_id in self._adjacency[node_id]:
            if neighbor_id in self._nodes:
                neighbors.append(self._nodes[neighbor_id])
        
        if relationship:
            neighbors = [
                n for n in neighbors
                if self._has_relationship(node_id, n.id, relationship)
            ]
        
        return neighbors

    def _has_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> bool:
        for edge in self._edges.values():
            if (edge.source_id == source_id and edge.target_id == target_id and 
                edge.relationship == relationship):
                return True
            if (edge.source_id == target_id and edge.target_id == source_id and 
                edge.relationship == relationship):
                return True
        return False

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        
        visited = set()
        queue = [(source_id, [source_id])]
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target_id:
                return path
            
            if len(path) > max_depth:
                continue
            
            visited.add(current)
            
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        
        return None

    def get_connected_components(self) -> List[List[str]]:
        visited = set()
        components = []
        
        for node_id in self._nodes:
            if node_id not in visited:
                component = []
                stack = [node_id]
                
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.append(current)
                    
                    for neighbor in self._adjacency.get(current, set()):
                        if neighbor not in visited:
                            stack.append(neighbor)
                
                components.append(component)
        
        return components

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        
        del self._nodes[node_id]
        
        edges_to_remove = [
            edge_id for edge_id, edge in self._edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        for edge_id in edges_to_remove:
            del self._edges[edge_id]
        
        if node_id in self._adjacency:
            del self._adjacency[node_id]
        
        for adj_set in self._adjacency.values():
            adj_set.discard(node_id)
        
        self._save()
        return True

_graph_store: Optional[MemoryGraphStore] = None

def get_memory_graph_store() -> MemoryGraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = MemoryGraphStore()
    return _graph_store