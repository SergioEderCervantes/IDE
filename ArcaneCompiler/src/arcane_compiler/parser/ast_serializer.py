import json
from typing import Optional
from .ast_nodes import ASTNode


def ast_to_json(ast: Optional[ASTNode], success: bool, errors: list[str]) -> str:
    """
    Serializa el resultado del análisis sintáctico al formato JSON esperado por el IDE.
    Recibe el AST ya construido (ver ast_builder.build_ast).
    """
    return json.dumps({
        "success": success,
        "ast": ast.to_dict() if ast is not None else None,
        "error_count": len(errors),
    }, indent=2, ensure_ascii=False)
