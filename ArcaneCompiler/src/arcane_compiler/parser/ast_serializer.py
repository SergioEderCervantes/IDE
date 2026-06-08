import json
from .ast_nodes import ASTNode


def ast_to_json(ast: ASTNode, success: bool, errors: list[str]) -> str:
    """
    Serializa el resultado del parser al formato JSON esperado por el IDE.

    Formato de salida:
    {
      "success": bool,
      "ast": { ... } | null,
      "error_count": int
    }
    """
    return json.dumps({
        "success": success,
        "ast": ast.to_dict() if ast is not None else None,
        "error_count": len(errors),
    }, indent=2, ensure_ascii=False)
