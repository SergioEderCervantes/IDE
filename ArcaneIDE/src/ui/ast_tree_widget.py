from PyQt6.QtWidgets import (
    QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor


_LEAF_KINDS = {
    "IDENTIFIER", "INTEGER", "REAL", "STRING_LITERAL", "CHAR_LITERAL",
    "KW_INT", "KW_FLOAT", "KW_BOOL", "KW_TRUE", "KW_FALSE",
    "KW_IF", "KW_ELSE", "KW_END", "KW_WHILE", "KW_DO", "KW_UNTIL",
    "KW_CIN", "KW_COUT", "KW_MAIN", "KW_THEN",
    "OP_PLUS", "OP_MINUS", "OP_MULTIPLY", "OP_DIVIDE", "OP_MODULO",
    "OP_POWER", "OP_INCREMENT", "OP_DECREMENT",
    "OP_LT", "OP_LE", "OP_GT", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR", "OP_NOT", "OP_NEG",
    "OP_ASSIGN", "OP_SHIFT_LEFT", "OP_SHIFT_RIGHT",
    "SYM_SEMICOLON", "SYM_COMMA", "SYM_LPAREN", "SYM_RPAREN",
    "CONV",
}

# Orden en que se muestran los atributos semánticos
_ORDEN_ATRIBUTOS = ["dtype", "tipo", "valor", "dir", "verificacion"]

_COLOR_ERROR = "#f38ba8"
_COLOR_CONVERSION = "#e5a50a"


class _ColorDelegate(QStyledItemDelegate):
    """Respeta el color propio de cada elemento (ForegroundRole).

    El tema qt-material define `QTreeView::item { color: ... }` en su hoja de estilos y
    esa regla anula el color por elemento. Para los elementos con color propio se dibuja
    el fondo con el estilo normal y el texto a mano con su color.
    """

    def paint(self, painter, option, index):
        color = index.data(Qt.ItemDataRole.ForegroundRole)
        if color is None:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = opt.widget
        style = widget.style() if widget else QApplication.style()
        rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, widget)
        texto = opt.text
        opt.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)
        painter.save()
        painter.setFont(opt.font)
        painter.setPen(color.color() if isinstance(color, QBrush) else QColor(color))
        texto = opt.fontMetrics.elidedText(texto, Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, int(opt.displayAlignment.value), texto)
        painter.restore()


class ASTTreeWidget(QTreeWidget):
    """Muestra un AST (el dict que produce el compilador).

    Con con_atributos=True agrega la columna "Atributos" con las anotaciones del
    análisis semántico (node["attrs"]); los nodos CONV se resaltan y las
    verificaciones fallidas se muestran en rojo.
    """

    def __init__(self, parent=None, titulo: str = "Árbol Sintáctico Abstracto",
                 con_atributos: bool = False):
        super().__init__(parent)
        self._con_atributos = con_atributos
        if con_atributos:
            self.setColumnCount(2)
            self.setHeaderLabels([titulo, "Atributos"])
        else:
            self.setColumnCount(1)
            self.setHeaderLabel(titulo)
        self.setMinimumWidth(400)
        self.setItemDelegate(_ColorDelegate(self))

    def populate(self, ast_dict: dict) -> None:
        """Puebla el árbol con el AST y lo expande completamente."""
        self.clear()
        if not ast_dict:
            return
        root_item = self._build_item(ast_dict)
        self.addTopLevelItem(root_item)
        self.expandAll()
        if self._con_atributos:
            self.resizeColumnToContents(0)

    def clear_tree(self) -> None:
        self.clear()

    def _build_item(self, node: dict) -> QTreeWidgetItem:
        kind = node.get("kind", "?")
        value = node.get("value")
        line = node.get("line")
        col = node.get("col")

        if kind == "error":
            # El mensaje ya incluye línea y columna
            item = QTreeWidgetItem([f"⚠ {value}"])
            item.setForeground(0, QBrush(QColor(_COLOR_ERROR)))
            return item

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

        if self._con_atributos:
            attrs = node.get("attrs") or {}
            item = QTreeWidgetItem([label, _formato_atributos(attrs)])
            color = _color_de(kind, attrs)
            if color:
                for columna in (0, 1):
                    item.setForeground(columna, QBrush(QColor(color)))
        else:
            item = QTreeWidgetItem([label])

        for child in node.get("children", []):
            item.addChild(self._build_item(child))

        return item


def _formato_atributos(attrs: dict) -> str:
    claves = [k for k in _ORDEN_ATRIBUTOS if k in attrs] + [k for k in attrs if k not in _ORDEN_ATRIBUTOS]
    partes = []
    for clave in claves:
        valor = attrs[clave]
        if isinstance(valor, bool):
            valor = "true" if valor else "false"
        partes.append(str(valor) if clave == "verificacion" else f"{clave}={valor}")
    return "  ·  ".join(partes)


def _color_de(kind: str, attrs: dict):
    if attrs.get("tipo") == "error" or "✗" in str(attrs.get("verificacion", "")):
        return _COLOR_ERROR
    if kind == "CONV":
        return _COLOR_CONVERSION
    return None
