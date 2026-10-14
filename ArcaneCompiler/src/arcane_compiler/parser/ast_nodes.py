from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ASTNode:
    """Nodo del Árbol Sintáctico Abstracto.

    `attrs` guarda las anotaciones del análisis semántico (tipo, valor, dtype, dir, ...).
    En el AST que produce el análisis sintáctico siempre está vacío.
    """
    kind: str
    value: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    children: list[ASTNode] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)

    def add(self, child: ASTNode) -> ASTNode:
        """Agrega un hijo y retorna self para encadenamiento."""
        if child is not None:
            self.children.append(child)
        return self

    def to_dict(self) -> dict:
        """Serializa el nodo a dict para JSON."""
        return {
            "kind": self.kind,
            "value": self.value,
            "line": self.line,
            "col": self.col,
            "attrs": dict(self.attrs),
            "children": [c.to_dict() for c in self.children],
        }
