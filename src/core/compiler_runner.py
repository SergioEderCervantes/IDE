import re
import sys
import locale
from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class CompilerRunner(QObject):
    """
    Runs the external compiler script asynchronously and parses its output.
    """
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(dict)  # Emits a dictionary with parsed results
    compilation_error = pyqtSignal(str)      # Emits an error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)

        self._output_buffer = ""
        self._error_buffer = ""
        self._encodings = ["utf-8", locale.getpreferredencoding(False), "cp1252", "latin-1"]

    def _decode_process_output(self, data: bytes) -> str:
        """Decode process output robustly across platform default encodings."""
        for encoding in self._encodings:
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")

    def _run_compiler(self, source_file: str, phase: str):
        """Private method to start the compiler process."""
        self.compilation_started.emit()
        self._output_buffer = ""
        self._error_buffer = ""
        
        # Using sys.executable ensures we use the same python interpreter
        # and separating arguments is more robust.
        self.process.start(sys.executable, ["compiler/compiler.py", source_file, phase])

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

    def _handle_stdout(self):
        """Append standard output to the buffer."""
        data = bytes(self.process.readAllStandardOutput())
        self._output_buffer += self._decode_process_output(data)

    def _handle_stderr(self):
        """Append standard error to the buffer."""
        data = bytes(self.process.readAllStandardError())
        self._error_buffer += self._decode_process_output(data)

    def _handle_finished(self):
        """Called when the process is finished. Parses output and emits signals."""
        if self.process.exitStatus() != QProcess.ExitStatus.NormalExit or self.process.exitCode() != 0:
            error_message = self._error_buffer or "Compiler process failed to execute."
            self.compilation_error.emit(error_message)
        else:
            results = self._parse_output(self._output_buffer)
            self.compilation_finished.emit(results)

    def _parse_output(self, output: str) -> dict:
        """
        Parses the structured output from the compiler.
        Format: ===SECTION_NAME===...content...===END_SECTION_NAME===
        """
        results = {}
        # Regex to find all sections
        pattern = re.compile(r"""===(?P<name>\w+)===\r?\n(?P<content>.*?)===END_(?P=name)===""", re.DOTALL)
        
        for match in pattern.finditer(output):
            name = match.group('name').lower()
            content = match.group('content').strip()
            results[name] = content
            
        return results
