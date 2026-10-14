import re
import sys
import json as _json
import locale
from typing import Optional
from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class CompilerRunner(QObject):
    """
    Ejecuta el compilador externo (arcane-compiler) de manera asíncrona y parsea su salida.

    - compilation_finished(dict): el compilador terminó. Las llaves son las secciones en
      minúsculas (lexico, sintactico, ...). Las secciones JSON ya vienen parseadas:
        errores:        {lexico, sintactico, semantico: list[{linea, columna, mensaje}] | None,
                         avisos: list[str]}
        semantico:      {success, ast (anotado), recorrido: list[{linea, accion, detalle}],
                         error_count} | None
        tabla_simbolos: list[{nombre, tipo, direccion, declaracion, referencias}] | None
    - compilation_error(str): el compilador no pudo ejecutarse o falló (mensaje para el usuario).
    """
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(dict)
    compilation_error = pyqtSignal(str)
    ast_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Inicializacion de atributos"""
        super().__init__(parent)
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_process_error)

        # La salida se acumula en bytes y se decodifica al terminar: los pedazos que entrega
        # QProcess pueden cortar un carácter UTF-8 (á, ←, ✓) a la mitad
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._encodings = ["utf-8", locale.getpreferredencoding(False), "cp1252", "latin-1"]

    def _decode_process_output(self, data: bytes) -> str:
        """Decodifica el output de la manera que el SO acepte"""
        for encoding in self._encodings:
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")

    def is_running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def _run_compiler(self, source_file: str, phase: str):
        """Inicia el proceso de compilacion (se ignora si ya hay una en curso)"""
        if self.is_running():
            return
        self.compilation_started.emit()
        self._stdout = bytearray()
        self._stderr = bytearray()
        self.process.start(sys.executable, ["-m", "arcane_compiler.main", source_file, phase])

    def _handle_stdout(self):
        """Acumula la salida normal"""
        self._stdout += bytes(self.process.readAllStandardOutput())      # type: ignore

    def _handle_stderr(self):
        """Acumula la salida de error"""
        self._stderr += bytes(self.process.readAllStandardError())       # type: ignore

    def _handle_process_error(self, error: QProcess.ProcessError):
        """Si el proceso ni siquiera arranca, Qt no emite finished: se avisa aquí."""
        if error == QProcess.ProcessError.FailedToStart:
            self.compilation_error.emit(
                f"No se pudo iniciar el compilador ({self.process.program()} -m arcane_compiler.main).\n"
                "Verifica que 'arcane-compiler' esté instalado en el mismo entorno que el IDE."
            )

    def _handle_finished(self):
        """Callback que se ejecuta cuando el proceso termina, manda las señales con el output parseado"""
        salida = self._decode_process_output(bytes(self._stdout))
        errores = self._decode_process_output(bytes(self._stderr))

        # Código distinto de 0 = invocación inválida o falla interna del compilador.
        # Los errores del programa fuente salen con código 0 dentro de la sección ERRORES.
        if self.process.exitStatus() != QProcess.ExitStatus.NormalExit or self.process.exitCode() != 0:
            error_message = (
                errores.strip()
                or salida.strip()
                or f"El compilador terminó inesperadamente (código {self.process.exitCode()})."
            )
            self.compilation_error.emit(error_message)
            return

        results = self._parse_output(salida)
        if results is None:
            inicio = (salida.strip() or errores.strip() or "(sin salida)")[:500]
            self.compilation_error.emit(
                "La salida del compilador no es válida (falta la sección ERRORES o no tiene el "
                f"formato esperado).\n\nInicio de la salida:\n{inicio}"
            )
            return

        ast = results.pop("_ast", None)
        if ast:  # mostrar el árbol aunque haya errores sintácticos
            self.ast_ready.emit(ast)
        self.compilation_finished.emit(results)

    def _parse_output(self, output: str) -> Optional[dict]:
        """
        Parsea el output por secciones
        Formato: ===SECTION_NAME===...content...===END_SECTION_NAME===

        Devuelve None si la salida no cumple el protocolo (ERRORES ausente o malformado).
        Las secciones JSON opcionales con un formato inesperado se tratan como ausentes.
        """
        results: dict = {}
        pattern = re.compile(r"""===(?P<name>\w+)===\r?\n(?P<content>.*?)===END_(?P=name)===""", re.DOTALL)

        for match in pattern.finditer(output):
            name = match.group('name').lower()
            content = match.group('content').strip()
            results[name] = content

        errores = _json_o_none(results.get("errores"))
        if not _errores_validos(errores):
            return None
        results["errores"] = errores

        sintactico = _json_o_none(results.get("sintactico"))
        if isinstance(sintactico, dict) and isinstance(sintactico.get("ast"), dict):
            results["_ast"] = sintactico["ast"]

        semantico = _json_o_none(results.get("semantico"))
        results["semantico"] = (
            semantico if isinstance(semantico, dict) and _lista_de_dicts(semantico.get("recorrido", []))
            else None
        )
        tabla = _json_o_none(results.get("tabla_simbolos"))
        results["tabla_simbolos"] = tabla if _lista_de_dicts(tabla) else None

        return results

    # Metodos publicos para iniciar la compilacion por fases
    def run_lexical_analysis(self, source_file: str) -> None:
        self._run_compiler(source_file, "lexical")

    def run_syntactic_analysis(self, source_file: str) -> None:
        self._run_compiler(source_file, "syntactic")

    def run_semantic_analysis(self, source_file: str) -> None:
        self._run_compiler(source_file, "semantic")

    def run_intermediate_generation(self, source_file: str) -> None:
        self._run_compiler(source_file, "intermediate")

    def run_execution(self, source_file: str) -> None:
        self._run_compiler(source_file, "execution")


def _json_o_none(texto: Optional[str]):
    """JSON de una sección, o None si está vacía o no es JSON válido."""
    try:
        return _json.loads(texto or "null")
    except ValueError:
        return None


def _lista_de_dicts(valor) -> bool:
    return isinstance(valor, list) and all(isinstance(x, dict) for x in valor)


def _errores_validos(errores) -> bool:
    """ERRORES = {lexico, sintactico, semantico: list[dict] | None, avisos: list[str]}."""
    if not isinstance(errores, dict):
        return False
    for fase in ("lexico", "sintactico", "semantico"):
        lista = errores.get(fase)
        if lista is not None and not _lista_de_dicts(lista):
            return False
    avisos = errores.get("avisos", [])
    return isinstance(avisos, list) and all(isinstance(a, str) for a in avisos)