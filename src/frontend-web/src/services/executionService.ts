import { useAuthStore } from '../store/authStore';

type State = 'queued' | 'executing' | 'completed' | 'error';

interface RunCallbacks {
  onStatus: (msg: string) => void;
  onStdout: (data: string) => void;
  onStderr: (data: string) => void;
  onStateChange: (state: State) => void;
  onDone: (exitCode: number) => void;
  onError: (msg: string) => void;
}

class ExecutionService {
  private ws: WebSocket | null = null;

  runCode(
    code: string,
    language: string,
    stdin: string,
    cb: RunCallbacks,
  ): Promise<void> {
    const { token, user } = useAuthStore.getState();
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/execute`;
    this.ws = new WebSocket(wsUrl);

    return new Promise((resolve) => {
      const ws = this.ws!;

      ws.onopen = () => {
        ws.send(JSON.stringify({
          source_code: code,
          env_type: language,
          student_id: user?.userId || 'unknown',
          mode: 'interactive',
          stdin_data: stdin || '',
          token: token,
        }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const status = data.status;

        switch (status) {
          case 'queued':
            cb.onStateChange('queued');
            cb.onStatus(data.message || 'Queued...');
            break;
          case 'executing':
            cb.onStateChange('executing');
            cb.onStatus(data.message || 'Executing...');
            break;
          case 'stdout':
            cb.onStdout(data.stdout || '');
            break;
          case 'stderr':
            cb.onStderr(data.stderr || '');
            break;
          case 'completed':
            cb.onStateChange('completed');
            if (data.stdout) cb.onStdout(data.stdout);
            if (data.stderr) cb.onStderr(data.stderr);
            cb.onDone(data.exit_code ?? 0);
            this.cleanup();
            resolve();
            break;
          case 'compile_error':
            cb.onStateChange('error');
            cb.onError(data.message || 'Compilation failed');
            if (data.stderr) cb.onStderr(data.stderr);
            this.cleanup();
            resolve();
            break;
          case 'error':
            cb.onStateChange('error');
            cb.onError(data.message || 'Execution failed');
            this.cleanup();
            resolve();
            break;
          default:
            if (data.stdout) cb.onStdout(data.stdout);
            if (data.stderr) cb.onStderr(data.stderr);
        }
      };

      ws.onerror = () => {
        cb.onStateChange('error');
        cb.onError('WebSocket connection error. Is the server running?');
        this.cleanup();
        resolve();
      };

      ws.onclose = () => {
        this.ws = null;
      };
    });
  }

  runWasm(
    _language: string,
    code: string,
    stdin: string,
    cb: RunCallbacks,
  ): Promise<void> {
    return this._runPyodide(code, stdin, cb);
  }

  private async _runPyodide(code: string, stdin: string, cb: RunCallbacks) {
    cb.onStateChange('executing');
    cb.onStatus('Initializing Pyodide (in-browser)...');

    let pyodide: any = null;
    const win = window as any;
    if (typeof win.loadPyodide === 'function') {
      try {
        pyodide = await win.loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
        });
      } catch (e: any) {
        cb.onStateChange('error');
        cb.onError('Failed to load Pyodide WASM: ' + (e.message || e));
        return;
      }
    } else {
      cb.onStateChange('error');
      cb.onError('Pyodide not available in browser. Use K8s Python instead.');
      return;
    }

    pyodide.setStdout({ batched: (msg: string) => cb.onStdout(msg + '\r\n') });
    pyodide.setStderr({ batched: (msg: string) => cb.onStderr(msg + '\r\n') });

    const stdinLines = stdin ? stdin.split('\n') : [];
    let stdinIndex = 0;
    pyodide.setStdin({
      stdin: () => {
        if (stdinIndex < stdinLines.length) {
          return stdinLines[stdinIndex++];
        }
        return '';
      },
      error: false,
      isatty: false,
    });

    try {
      const result = await pyodide.runPythonAsync(code);
      if (result !== undefined) {
        cb.onStdout(String(result) + '\r\n');
      }
      cb.onStateChange('completed');
      cb.onDone(0);
    } catch (err: any) {
      const msg = err.message || String(err);
      const lastLine = msg.split('\n').filter((l: string) => l.trim()).pop() || msg;
      cb.onStderr('\x1b[31m' + msg + '\x1b[0m\r\n');
      cb.onStateChange('error');
      cb.onError(lastLine);
    }
  }

  sendStdin(data: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ stdin_data: data }));
    }
  }

  closeStdin() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ close_stdin: true }));
    }
  }

  cancel() {
    if (this.ws) {
      this.ws.close(1000, 'cancelled');
      this.ws = null;
    }
  }

  private cleanup() {
    this.ws = null;
  }
}

export const executionService = new ExecutionService();
