import re
import sys
import json as _json
import locale
from pathlib import Path
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

        self._output_buffer = ""
        self._error_buffer = ""
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
        self._output_buffer = ""
        self._error_buffer = ""
        
        _compiler_bin = Path(sys.executable).parent / "arcane-compiler"
        self.process.start(str(_compiler_bin), [source_file, phase])

    def _handle_stdout(self):
        """Maneja el buffer de output normal"""
        data = bytes(self.process.readAllStandardOutput())      # type: ignore
        self._output_buffer += self._decode_process_output(data)

    def _handle_stderr(self):
        """Maneja el buffer de output de error"""
        data = bytes(self.process.readAllStandardError())       # type: ignore
        self._error_buffer += self._decode_process_output(data)

    def _handle_process_error(self, error: QProcess.ProcessError):
        """Si el proceso ni siquiera arranca, Qt no emite finished: se avisa aquí."""
        if error == QProcess.ProcessError.FailedToStart:
            self.compilation_error.emit(
                f"No se pudo iniciar el compilador ({self.process.program()}).\n"
                "Verifica que 'arcane-compiler' esté instalado en el mismo entorno que el IDE."
            )

    def _handle_finished(self):
        """Callback que se ejecuta cuando el proceso termina, manda las señales con el output parseado"""
        # Código distinto de 0 = invocación inválida o falla interna del compilador.
        # Los errores del programa fuente salen con código 0 dentro de la sección ERRORES.
        if self.process.exitStatus() != QProcess.ExitStatus.NormalExit or self.process.exitCode() != 0:
            error_message = (
                self._error_buffer.strip()
                or self._output_buffer.strip()
                or f"El compilador terminó inesperadamente (código {self.process.exitCode()})."
            )
            self.compilation_error.emit(error_message)
        else:
            results = self._parse_output(self._output_buffer)
            self.compilation_finished.emit(results)

    def _parse_output(self, output: str) -> dict:
        """
        Parsea el output por secciones
        Formato: ===SECTION_NAME===...content...===END_SECTION_NAME===
        """
        results = {}
        pattern = re.compile(r"""===(?P<name>\w+)===\r?\n(?P<content>.*?)===END_(?P=name)===""", re.DOTALL)
        
        for match in pattern.finditer(output):
            name = match.group('name').lower()
            content = match.group('content').strip()
            results[name] = content

        if results.get("sintactico"):
            try:
                data = _json.loads(results["sintactico"])
                if data.get("ast"):  # mostrar árbol aunque haya errores sintácticos
                    self.ast_ready.emit(data["ast"])
            except (ValueError, KeyError):
                pass

        # Secciones JSON: se entregan ya parseadas (None si la fase no se ejecutó)
        for seccion in ("errores", "semantico", "tabla_simbolos"):
            try:
                results[seccion] = _json.loads(results.get(seccion) or "null")
            except ValueError:
                results[seccion] = None

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