import subprocess
import os
import tempfile
import re
import time
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Callable

from lib.config import get_settings
from lib.logger import log
from lib.models import ExecutionResult
from lib.utils import format_error_message


class BaseExecutor(ABC):
    """Base class for language-specific code executors"""

    def __init__(self):
        settings = get_settings()
        self.timeout = settings.execution_timeout
        self.maxMemory = settings.max_memory_mb
        self.maxFileSize = settings.max_file_size_mb
        self.env = settings.env

    def execute(
        self,
        code: str,
        filename: str,
        on_output: Callable[[bytes], None],
        input_queue: Any,
    ) -> ExecutionResult:
        """
        Execute code with PTY streaming

        Args:
            code: Source code to execute
            filename: Filename for the code
            on_output: Callback function(data) called with raw PTY output
            input_queue: Queue to get user input from

        Returns:
            {"success": bool, "exit_code": int, "execution_time": float}
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self._writeToFile(tmpdir, code, filename)
            command = self._build_command(filepath, tmpdir)
            result = self._execute_pty(command, tmpdir, on_output, input_queue)
            return result

    def _writeToFile(self, tmpDir: str, code: str, filename: str) -> str:
        """
        Write code to temporary file used during execution

        Returns:
            str: path to file
        """
        self._validateFileName(filename)
        filepath = os.path.join(tmpDir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        return filepath

    def _validateFileName(self, filename: str):
        """Validates file name uses appropriate characters"""

        if not re.match(r"^[a-zA-Z0-9_.-]+$", filename):
            raise ValueError(f"Invalid filename: {filename}")

        # Prevent any Traversal
        if ".." in filename or filename.startswith("/"):
            raise ValueError(f"Invalid filename: {filename}")

    def _build_sandbox_command(self, command: List[str], workdir: str) -> List[str]:
        """
        Build Firejail sandbox command with security restrictions

        Args:
            command: Command to execute
            workdir: Working directory

        Returns:
            Complete firejail command with restrictions
        """


        base_cmd = [
            "/usr/bin/firejail",
            "--quiet", # Suppress warning that were in docker container
            "--profile=/etc/firejail/sandbox.profile",
            "--nodbus",
            f"--rlimit-cpu={self.timeout}",
            f"--rlimit-fsize={self.maxFileSize * 1024 * 1024}",
            f"--timeout=00:00:{self.timeout:02d}",
        ] 

        # Js/Node needs more waaay more vram than other languages. 
        is_javascript = any(
            keyword in cmd.lower() 
            for cmd in command 
            for keyword in ['node', 'nodejs', 'javascript']
        )

        if not is_javascript:
            base_cmd.append(f"--rlimit-as={self.maxMemory * 1024 * 1024}")
        
        return base_cmd + command

    def _format_error_result(
        self, error: Exception, execution_time: float
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Execution error: {str(error)}",
            exit_code=-1,
            execution_time=execution_time,
        )

    def _execute_pty(
        self,
        command: List[str],
        workdir: str,
        on_output: Callable[[bytes], None],
        input_queue: Any,
    ) -> Dict[str, Any]:
        import pty
        import select
        import os
        import fcntl
        import struct
        import termios

        start_time = time.time()

        try:
            master_fd, slave_fd = pty.openpty()
            winsize = struct.pack("HHHH", 24, 80, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            sandbox_command = self._build_sandbox_command(command, workdir)
            process = subprocess.Popen(
                sandbox_command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=workdir,
                preexec_fn=os.setsid,
            )

            os.close(slave_fd)
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            complete_output = b""

            while True:
                # Check for PTY output
                readable, _, _ = select.select([master_fd], [], [], 0.01)

                if master_fd in readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            complete_output += data
                            cleaned_data = self._clean_output(data, workdir)
                            on_output(cleaned_data.encode("utf-8"))
                        else:
                            break # Break early to not wait for cleanup
                    except OSError:
                        break

                # Check for user input
                try:
                    user_input = input_queue.get_nowait()
                    os.write(master_fd, user_input.encode("utf-8"))
                except Exception:
                    pass

                # Safety timeout
                if time.time() - start_time > self.timeout:
                    process.kill()
                    break

            os.close(master_fd)
            
            # Wait for process cleanup (but don't block UI on this)
            # Use a short timeout so Firejail cleanup doesn't delay response
            try:
                process.wait(timeout=0.5)  # ← Give it 500ms max
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if still cleaning up
                process.wait()

            execution_time = time.time() - start_time
            return_code = process.returncode if process.returncode is not None else -1

            return ExecutionResult(
                success=process.returncode == 0,
                exit_code=return_code,
                execution_time=execution_time,
                stdout=complete_output.decode("utf-8", errors="replace"),
                stderr="",
            )

        except Exception as e:
            if self.env == "development":
                traceback.print_exc()
            execution_time = time.time() - start_time
            return self._format_error_result(e, execution_time)

    def _clean_output(self, data: bytes, workdir: str) -> str:

        try:
            text = data.decode("utf-8", errors="replace")

            # Only format looks error (contains "Error" or "Traceback")
            if "Error:" in text or "Traceback" in text or "Exception" in text:
                # Determine language from command (stored in self if needed)
                # For now, detect from error format
                language = (
                    "javascript" if "Error:" in text and "at " in text else "python"
                )
                text = format_error_message(text, language, workdir)
            else:
                # Just strip ANSI codes from regular output
                from lib.utils.output_formatter import strip_ansi_codes

                text = strip_ansi_codes(text)

            return text
        except Exception as e:
            # If cleaning fails, return original
            log.warning(f"Failed to clean output: {e}")
            return data.decode("utf-8", errors="replace")

    @abstractmethod
    def _build_command(self, filepath: str, workdir: str) -> List[str]:
        """
        Build language-specific execution command

        Interpreted languages:
            Return [interpreter command, filepath]

        Compiled languages:
            Compile the code first, then return the binary path

        Args:
            filepath: Path to the code file
            workdir: Working directory for execution

        Returns:
            List of command arguments to execute the code

        Raises:
            Exception: If compilation or command building fails
        """
        pass
