import { useWorkspaceStore } from '../store/workspaceStore';

const WS_BASE = `ws://${window.location.host}`;

export class WasmExecutor {
  private pyodide: any = null;
  private isInitializing: boolean = false;

  async initPyodide() {
    if (this.pyodide) return;
    if (this.isInitializing) {
      while (this.isInitializing) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return;
    }

    this.isInitializing = true;
    try {
      const win = window as any;
      if (typeof win.loadPyodide === 'function') {
        this.pyodide = await win.loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/'
        });
      } else {
        throw new Error('Pyodide script not found in window');
      }
    } catch (err) {
      console.error('Failed to init Pyodide:', err);
    } finally {
      this.isInitializing = false;
    }
  }

  async runPython(code: string): Promise<void> {
    const { appendTerminalOutput } = useWorkspaceStore.getState();
    await this.initPyodide();
    if (!this.pyodide) {
      appendTerminalOutput('Error: Pyodide failed to load.\r\n');
      return;
    }

    try {
      this.pyodide.setStdout({ batched: (msg: string) => appendTerminalOutput(msg + '\r\n') });
      this.pyodide.setStderr({ batched: (msg: string) => appendTerminalOutput(msg + '\r\n') });
      
      const result = await this.pyodide.runPythonAsync(code);
      if (result !== undefined) {
        appendTerminalOutput(String(result) + '\r\n');
      }
    } catch (err: any) {
      appendTerminalOutput(err.toString() + '\r\n');
    }
  }

  async runCpp(code: string): Promise<void> {
    const { appendTerminalOutput } = useWorkspaceStore.getState();
    appendTerminalOutput('Compiling & executing C++ via server (local WASM path)...\r\n');

    const studentUser = this._getStoredUser();
    const ws = new WebSocket(`${WS_BASE}/ws/execute`);

    return new Promise((resolve) => {
      ws.onopen = () => {
        ws.send(JSON.stringify({
          source_code: code,
          env_type: 'cpp-basic',
          student_id: studentUser?.userId || 'unknown',
          mode: 'batch',
          stdin_data: '',
        }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const status = data.status;

        if (status === 'queued' || status === 'executing') {
          if (data.message) appendTerminalOutput(data.message + '\r\n');
        } else if (status === 'completed') {
          if (data.stdout) appendTerminalOutput(data.stdout);
          if (data.stderr) appendTerminalOutput('STDERR: ' + data.stderr + '\r\n');
          if (data.exit_code !== undefined) {
            appendTerminalOutput(`\r\nProcess exited with code ${data.exit_code}\r\n`);
          }
          ws.close();
          resolve();
        } else if (status === 'error') {
          appendTerminalOutput('Error: ' + (data.message || 'Execution failed') + '\r\n');
          ws.close();
          resolve();
        }
      };

      ws.onerror = () => {
        appendTerminalOutput('WebSocket connection error. Is the server running?\r\n');
        resolve();
      };
    });
  }

  private _getStoredUser(): { userId: string; role: string } | null {
    const stored = localStorage.getItem('eci_user');
    return stored ? JSON.parse(stored) : null;
  }
}

export const wasmExecutor = new WasmExecutor();
