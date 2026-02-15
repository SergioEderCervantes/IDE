import re
from PySide6.QtCore import QObject, QProcess, Signal

class CompilerRunner(QObject):
    """
    Runs the external compiler script asynchronously and parses its output.
    """
    compilation_started = Signal()
    compilation_finished = Signal(dict)  # Emits a dictionary with parsed results
    compilation_error = Signal(str)      # Emits an error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)

        self._output_buffer = ""
        self._error_buffer = ""

    def _run_compiler(self, source_file: str, phase: str):
        """Private method to start the compiler process."""
        self.compilation_started.emit()
        self._output_buffer = ""
        self._error_buffer = ""
        
        # In the future, we can pass the phase to the compiler
        # For now, the dummy compiler runs all phases at once.
        # command = f"python compiler/compiler.py {source_file} --phase={phase}"
        command = f"python compiler/compiler.py {source_file}"
        self.process.start(command)

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
        self._output_buffer += self.process.readAllStandardOutput().data().decode()

    def _handle_stderr(self):
        """Append standard error to the buffer."""
        self._error_buffer += self.process.readAllStandardError().data().decode()

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
        pattern = re.compile(r"===(?P<name>\w+)===
(?P<content>.*?)===END_\w+===", re.DOTALL)
        
        for match in pattern.finditer(output):
            name = match.group('name').lower()
            content = match.group('content').strip()
            results[name] = content
            
        return results
