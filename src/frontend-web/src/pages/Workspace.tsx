import React, { useEffect } from 'react';
import { CodeEditor } from '../components/CodeEditor';
import { Terminal } from '../components/Terminal';
import { useWorkspaceStore } from '../store/workspaceStore';
import { wasmExecutor } from '../wasm/WasmExecutor';
import { useNavigate } from 'react-router-dom';

export const Workspace: React.FC = () => {
  const { code, setCode, language, setLanguage, clearTerminal, appendTerminalOutput } = useWorkspaceStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Pre-initialize Pyodide on component mount
    wasmExecutor.initPyodide().catch(console.error);
  }, []);

  const handleRunCode = async () => {
    clearTerminal();
    appendTerminalOutput('Executing...\r\n');
    
    if (language === 'python') {
      await wasmExecutor.runPython(code);
    } else {
      await wasmExecutor.runCpp(code);
    }
    
    appendTerminalOutput('\r\nExecution finished.\r\n');
  };

  return (
    <div className="flex flex-col h-screen bg-[#121212] text-white">
      {/* Top Navbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-gray-800">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white">
            &larr; Back
          </button>
          <h1 className="text-xl font-bold text-[#aa3bff]">Ace Workspace</h1>
        </div>
        <div className="flex items-center space-x-4">
          <select 
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#2d2d2d] border border-gray-700 text-white rounded px-2 py-1 outline-none"
          >
            <option value="python">Python (WASM)</option>
            <option value="cpp">C++ (K8s / Engine)</option>
          </select>
          <button 
            onClick={handleRunCode}
            className="bg-[#aa3bff] hover:bg-[#912ee6] px-4 py-1 rounded font-semibold transition-colors cursor-pointer"
          >
            Run
          </button>
        </div>
      </div>

      {/* Main Content Split */}
      <div className="flex flex-1 overflow-hidden">
        {/* Editor Area */}
        <div className="flex-1 border-r border-gray-800">
          <CodeEditor 
            language={language}
            value={code}
            onChange={(val) => setCode(val || '')}
          />
        </div>

        {/* Terminal Area */}
        <div className="w-1/3 flex flex-col">
          <div className="px-4 py-2 bg-[#1e1e1e] border-b border-gray-800 text-sm font-semibold">
            Terminal
          </div>
          <div className="flex-1">
            <Terminal />
          </div>
        </div>
      </div>
    </div>
  );
};
