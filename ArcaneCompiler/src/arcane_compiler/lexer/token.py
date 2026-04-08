from dataclasses import dataclass
from .token_type import TokenType


@dataclass
class Token:
    type: TokenType
    value: str
    line: int    # 1-based
    column: int  # 1-based, columna donde empieza el token

    def __str__(self) -> str:
        return f"[{self.line}:{self.column}] {self.type.name:<25} {self.value!r}"
