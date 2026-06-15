/**
 * WasmExecutor
 * Handles execution of standard algorithms directly in the user's browser using WebAssembly.
 * This is meant to reduce cloud costs as specified in the architecture.
 */
import { useWorkspaceStore } from '../store/workspaceStore';

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
    appendTerminalOutput('C++ WASM Execution not yet fully integrated.\r\n');
  }
}

export const wasmExecutor = new WasmExecutor();
