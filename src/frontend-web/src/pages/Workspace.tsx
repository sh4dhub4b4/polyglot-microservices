import React, { useCallback } from 'react';
import { CodeEditor } from '../components/CodeEditor';
import { Terminal } from '../components/Terminal';
import { FileExplorer } from '../components/FileExplorer';
import { useWorkspaceStore } from '../store/workspaceStore';
import { executionService } from '../services/executionService';
import { useAuthStore } from '../store/authStore';
import { useNavigate } from 'react-router-dom';

const LANGUAGES = [
  { value: 'python-ds', label: 'Python (K8s Engine)' },
  { value: 'cpp-basic', label: 'C++ (K8s Engine)' },
  { value: 'go-sys', label: 'Go (K8s Engine)' },
  { value: 'node-js', label: 'Node.js (K8s Engine)' },
  { value: 'rust-sys', label: 'Rust (K8s Engine)' },
  { value: 'python-wasm', label: 'Python (In-Browser WASM)' },
];

export const Workspace: React.FC = () => {
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();
  const {
    code, setCode, language, setLanguage,
    stdin, setStdin,
    appendTerminalOutput, clearTerminal,
    executionState, setExecutionState, executionError, setExecutionError,
    activeFileId, files, addFile, removeFile, renameFile, setActiveFileId, updateFileContent,
  } = useWorkspaceStore();

  const handleRunCode = useCallback(async () => {
    if (executionState === 'executing' || executionState === 'queued') return;

    clearTerminal();
    setExecutionState('queued');
    setExecutionError(null);

    appendTerminalOutput(`\x1b[36mStarting execution (${language})...\x1b[0m\r\n`);

    const cb = {
      onStatus: (msg: string) => appendTerminalOutput(`\x1b[33m${msg}\x1b[0m\r\n`),
      onStdout: (data: string) => appendTerminalOutput(data),
      onStderr: (data: string) => appendTerminalOutput(`\x1b[31m${data}\x1b[0m\r\n`),
      onStateChange: (state: 'queued' | 'executing' | 'completed' | 'error') => setExecutionState(state),
      onDone: (exitCode: number) => {
        appendTerminalOutput(`\r\n\x1b[32mProcess exited with code ${exitCode}\x1b[0m\r\n`);
      },
      onError: (msg: string) => {
        setExecutionError(msg);
        appendTerminalOutput(`\r\n\x1b[31mError: ${msg}\x1b[0m\r\n`);
      },
    };

    if (language === 'python-wasm') {
      await executionService.runWasm(language, code, stdin, cb);
    } else {
      await executionService.runCode(code, language, stdin, cb);
    }
  }, [code, language, stdin, executionState, clearTerminal, setExecutionState, setExecutionError, appendTerminalOutput]);

  const handleCancel = useCallback(() => {
    executionService.cancel();
    setExecutionState('idle');
    appendTerminalOutput('\r\n\x1b[33mExecution cancelled.\x1b[0m\r\n');
  }, [setExecutionState, appendTerminalOutput]);

  const handleStdinInput = useCallback((data: string) => {
    executionService.sendStdin(data);
  }, []);

  const handleEditorChange = useCallback((val: string | undefined) => {
    const newCode = val || '';
    setCode(newCode);
    if (activeFileId) {
      updateFileContent(activeFileId, newCode);
    }
  }, [activeFileId, setCode, updateFileContent]);

  const isRunning = executionState === 'executing' || executionState === 'queued';
  const langLabel = LANGUAGES.find(l => l.value === language)?.label || language;

  return (
    <div className="flex flex-col h-screen bg-[#121212] text-white">
      {/* Top Navbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-gray-800 shrink-0">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white">
            &larr; Dashboard
          </button>
          <h1 className="text-xl font-bold text-[#aa3bff]">Ace Workspace</h1>
          {user && (
            <span className="text-sm text-gray-500">
              {user.displayName} ({user.role})
            </span>
          )}
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#2d2d2d] border border-gray-700 text-white rounded px-2 py-1 outline-none text-sm"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>

          {isRunning ? (
            <button
              onClick={handleCancel}
              className="bg-red-600 hover:bg-red-700 px-4 py-1 rounded font-semibold transition-colors text-sm"
            >
              ⏹ Stop
            </button>
          ) : (
            <button
              onClick={handleRunCode}
              className="bg-[#aa3bff] hover:bg-[#912ee6] px-4 py-1 rounded font-semibold transition-colors text-sm"
            >
              {executionState === 'completed' ? '▶ Run Again' : '▶ Run'}
            </button>
          )}

          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="text-gray-500 hover:text-white text-sm ml-2"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Execution status bar */}
      {executionState !== 'idle' && (
        <div className={`px-4 py-1 text-xs font-mono border-b shrink-0 ${
          executionState === 'error' ? 'bg-red-900/30 border-red-800 text-red-300' :
          executionState === 'completed' ? 'bg-green-900/30 border-green-800 text-green-300' :
          'bg-blue-900/30 border-blue-800 text-blue-300'
        }`}>
          {executionState === 'queued' && '⏳ Queued... waiting for cluster resources'}
          {executionState === 'executing' && `⚙️ Executing (${langLabel})...`}
          {executionState === 'completed' && '✅ Execution finished'}
          {executionState === 'error' && `❌ ${executionError || 'Execution failed'}`}
        </div>
      )}

      {/* Main Content: 3-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: File Explorer */}
        <div className="w-56 border-r border-gray-800 shrink-0">
          <FileExplorer
            files={files}
            activeFileId={activeFileId}
            onSelectFile={(id) => setActiveFileId(id)}
            onAddFile={(file) => addFile(file)}
            onRemoveFile={(id) => removeFile(id)}
            onRenameFile={(id, name) => renameFile(id, name)}
          />
        </div>

        {/* Center: Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1">
            <CodeEditor
              language={language}
              value={code}
              onChange={handleEditorChange}
            />
          </div>
        </div>

        {/* Right: Terminal + STDIN */}
        <div className="w-96 flex flex-col border-l border-gray-800 shrink-0">
          {/* Terminal */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="px-3 py-1.5 bg-[#1e1e1e] border-b border-gray-800 text-xs font-semibold text-gray-400 shrink-0">
              Terminal
            </div>
            <div className="flex-1 min-h-0">
              <Terminal onInput={handleStdinInput} />
            </div>
          </div>

          {/* STDIN Input */}
          <div className="h-32 border-t border-gray-800 flex flex-col shrink-0">
            <div className="px-3 py-1.5 bg-[#1e1e1e] border-b border-gray-800 text-xs font-semibold text-gray-400 shrink-0">
              Standard Input
            </div>
            <textarea
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              className="flex-1 bg-[#1e1e1e] text-white p-2 text-sm font-mono outline-none resize-none"
              placeholder="Enter input for your program here..."
              disabled={isRunning}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
