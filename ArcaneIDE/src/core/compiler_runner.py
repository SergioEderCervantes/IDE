import re
import sys
import locale
from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class CompilerRunner(QObject):
    """
    Runs the external compiler script asynchronously and parses its output.
    Ejecuta el programa compilador externo de manera asincrona y parsea el output:
    Output de compilacion exitosa: Diccionario [fase]=output
    Output de compilacion de error: String de error
    """
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(dict) 
    compilation_error = pyqtSignal(str)

    def __init__(self, parent=None):
        """Inicializacion de atributos"""
        super().__init__(parent)
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)

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

    def _run_compiler(self, source_file: str, phase: str):
        """Inicia el proceso de compilacion"""
        self.compilation_started.emit()
        self._output_buffer = ""
        self._error_buffer = ""
        
        self.process.start(sys.executable, ["compiler/compiler.py", source_file, phase])

    def _handle_stdout(self):
        """Maneja el buffer de output normal"""
        data = bytes(self.process.readAllStandardOutput())      # type: ignore
        self._output_buffer += self._decode_process_output(data)

    def _handle_stderr(self):
        """Maneja el buffer de output de error"""
        data = bytes(self.process.readAllStandardError())       # type: ignore
        self._error_buffer += self._decode_process_output(data)

    def _handle_finished(self):
        """Callback que se ejecuta cuando el proceso termina, manda las señales con el output parseado"""
        if self.process.exitStatus() != QProcess.ExitStatus.NormalExit or self.process.exitCode() != 0:
            error_message = self._error_buffer or "Compiler process failed to execute."
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