import subprocess
import os
import tempfile
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from config.settings import get_settings
from api.models.validators import validateFileName
from logger.logger import log

class BaseExecutor(ABC):
    """Base class for language-specific code executors"""

    def __init__(self):
            settings = get_settings()
            self.timeout = settings.execution_timeout
            self.maxMemory = settings.max_memory_mb
            self.maxFileSize =  settings.max_file_size_mb

    def execute(
        self,
        code: str,
        filename: str,
        on_output: Callable[[bytes], None],
        input_queue: Any
    ) -> Dict[str, Any]:
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
            result = self._execute_pty(
                command, tmpdir, on_output, input_queue
            )
            return result

    def _writeToFile(self, tmpDir: str, code: str, filename: str) -> str:
        """
        Write code to temporary file used during execution

        Returns:
            str: path to file
        """
        self._validateFileName(filename)
        filepath = os.path.join(tmpDir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        return filepath
    def _validateFileName(self, filename: str):
        """ Validates file name uses appropriate characters """

        if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
            raise ValueError(f"Invalid filename: {filename}")

        # Prevent any Traversal
        if '..' in filename or filename.startswith('/'):
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
        return [
            '/usr/bin/firejail',
            '--profile=/etc/firejail/sandbox.profile',
            f'--private={workdir}',
            '--net=none',
            '--nodbus',
            '--noroot',
            f'--rlimit-as={self.maxMemory * 1024 * 1024}',
            f'--rlimit-cpu={self.timeout}',
            f'--rlimit-fsize={self.maxFileSize * 1024 * 1024}',
            f'--timeout=00:00:{self.timeout:02d}',
        ] + command

    def _format_error_result(self, error: Exception, execution_time: float) -> Dict[str, Any]:
        """Format error result"""
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution error: {str(error)}",
            "exit_code": -1,
            "execution_time": execution_time
        }

    def _execute_pty(
        self,
        command: List[str],
        workdir: str,
        on_output: Callable[[bytes], None],
        input_queue: Any
    ) -> Dict[str, Any]:
        """
        Simple bidirectional pipe:
        - PTY output → on_output callback (sent to WebSocket)
        - input_queue → PTY input (from WebSocket)

        Args:
            command: Command to execute
            workdir: Working directory
            on_output: Callback(bytes) - receives raw PTY output
            input_queue: asyncio.Queue - provides user input

        Returns:
            Dict with execution results
        """
        import pty
        import select
        import os
        import fcntl
        import struct
        import termios

        start_time = time.time()

        try:
            master_fd, slave_fd = pty.openpty()

            # Set terminal size
            winsize = struct.pack('HHHH', 24, 80, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            sandbox_command = self._build_sandbox_command(command, workdir)

            process = subprocess.Popen(
                sandbox_command, 
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=workdir,
                preexec_fn=os.setsid
            )

            os.close(slave_fd)

            # Non-blocking master
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            complete_output = b""


            while True:
                # Check if process finished
                return_code = process.poll()
                if return_code is not None:
                    log.debug(f"Process exited with code {return_code}")
                    # Read any remaining output
                    try:
                        while True:
                            data = os.read(master_fd, 4096)
                            if not data:
                                break
                            complete_output += data
                            on_output(data)
                    except:
                        pass
                    break

                # Check for PTY output
                readable, _, _ = select.select([master_fd], [], [], 0.01)

                if master_fd in readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            complete_output += data
                            on_output(data)  # Stream immediately to WebSocket
                    except OSError:
                        pass

                # Check for user input (non-blocking)
                try:
                    user_input = input_queue.get_nowait()
                    os.write(master_fd, user_input.encode('utf-8'))
                except:
                    # Queue empty, continue
                    pass

                # Timeout
                if time.time() - start_time > self.timeout:
                    process.kill()
                    break

            os.close(master_fd)
            execution_time = time.time() - start_time

            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "execution_time": execution_time,
                "stdout": complete_output.decode('utf-8', errors='replace'),
                "stderr": ""
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            execution_time = time.time() - start_time
            return self._format_error_result(e, execution_time)

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
