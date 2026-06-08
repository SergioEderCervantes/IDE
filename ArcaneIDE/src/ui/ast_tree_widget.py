from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt


_LEAF_KINDS = {
    "IDENTIFIER", "INTEGER", "REAL", "STRING_LITERAL", "CHAR_LITERAL",
    "KW_INT", "KW_FLOAT", "KW_BOOL", "KW_TRUE", "KW_FALSE",
    "KW_IF", "KW_ELSE", "KW_END", "KW_WHILE", "KW_DO",
    "KW_CIN", "KW_COUT", "KW_MAIN", "KW_THEN",
    "OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_MODULO",
    "OP_POWER", "OP_INCREMENT", "OP_DECREMENT",
    "OP_LT", "OP_LE", "OP_GT", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR", "OP_NOT",
    "OP_ASSIGN", "OP_SHIFT_LEFT", "OP_SHIFT_RIGHT",
    "SYM_SEMICOLON", "SYM_COMMA", "SYM_LPAREN", "SYM_RPAREN",
}


class ASTTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Árbol Sintáctico Abstracto")
        self.setColumnCount(1)
        self.setMinimumWidth(400)

    def populate(self, ast_dict: dict) -> None:
        """Puebla el árbol con el AST y lo expande completamente."""
        self.clear()
        if not ast_dict:
            return
        root_item = self._build_item(ast_dict)
        self.addTopLevelItem(root_item)
        self.expandAll()

    def clear_tree(self) -> None:
        self.clear()

    def _build_item(self, node: dict) -> QTreeWidgetItem:
        kind = node.get("kind", "?")
        value = node.get("value")
        line = node.get("line")
        col = node.get("col")

        if kind in _LEAF_KINDS and value is not None:
            if line is not None:
                label = f"{kind}: {value!r}  [L{line}:C{col}]"
            else:
                label = f"{kind}: {value!r}"
        else:
            if line is not None:
                label = f"{kind}  [L{line}:C{col}]"
            else:
                label = kind

        item = QTreeWidgetItem([label])

        for child in node.get("children", []):
            item.addChild(self._build_item(child))

        return item
