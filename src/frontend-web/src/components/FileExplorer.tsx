import React, { useState } from 'react';
import type { FileNode } from '../store/workspaceStore';

interface FileExplorerProps {
  files: FileNode[];
  activeFileId: string | null;
  onSelectFile: (id: string) => void;
  onAddFile: (file: FileNode) => void;
  onRemoveFile: (id: string) => void;
  onRenameFile: (id: string, name: string) => void;
}

const FILE_ICONS: Record<string, string> = {
  python: '[🐍]',
  'cpp-basic': '[⚡]',
  'go-sys': '[🔷]',
  'node-js': '[🟢]',
  'rust-sys': '[🦀]',
  'python-ds': '[📊]',
  gui: '[🖥]',
};

const LANG_MAP: Record<string, string> = {
  py: 'python',
  cpp: 'cpp-basic',
  c: 'cpp-basic',
  go: 'go-sys',
  js: 'node-js',
  ts: 'node-js',
  rs: 'rust-sys',
};

function extToLang(name: string): string {
  const ext = name.split('.').pop() || '';
  return LANG_MAP[ext] || 'python';
}

let fileCounter = 0;

export const FileExplorer: React.FC<FileExplorerProps> = ({
  files, activeFileId, onSelectFile, onAddFile, onRemoveFile, onRenameFile,
}) => {
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState('');
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const handleAdd = () => {
    if (!newName.trim()) return;
    fileCounter++;
    const id = `file_${fileCounter}`;
    const lang = extToLang(newName);
    onAddFile({
      id,
      name: newName.trim(),
      content: getTemplate(lang),
      language: lang,
    });
    setNewName('');
    setShowNew(false);
  };

  const handleRename = (id: string) => {
    if (!renameValue.trim()) return;
    if (files.some(f => f.name === renameValue.trim() && f.id !== id)) return;
    onRenameFile(id, renameValue.trim());
    setRenamingId(null);
  };

  return (
    <div className="h-full flex flex-col bg-[#1e1e1e]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 shrink-0">
        <span className="text-xs font-semibold text-gray-400">Files</span>
        <button
          onClick={() => setShowNew(!showNew)}
          className="text-gray-500 hover:text-white text-sm px-1"
          title="New file"
        >
          +
        </button>
      </div>

      {showNew && (
        <div className="px-2 py-1 border-b border-gray-800 flex gap-1">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            className="flex-1 bg-[#2d2d2d] border border-gray-700 rounded px-2 py-0.5 text-xs text-white outline-none"
            placeholder="main.py"
            autoFocus
          />
          <button onClick={handleAdd} className="text-green-400 text-xs">Add</button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {files.length === 0 && (
          <div className="text-gray-600 text-xs text-center py-4">No files</div>
        )}
        {files.map((file) => {
          const isActive = file.id === activeFileId;
          const icon = FILE_ICONS[file.language] || '[📄]';
          const isRenaming = renamingId === file.id;

          return (
            <div
              key={file.id}
              className={`flex items-center px-3 py-1.5 cursor-pointer text-sm group ${
                isActive ? 'bg-[#2d2d2d] text-white' : 'text-gray-400 hover:text-white hover:bg-[#252525]'
              }`}
              onClick={() => onSelectFile(file.id)}
            >
              <span className="mr-1.5">{icon}</span>

              {isRenaming ? (
                <input
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRename(file.id);
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  onBlur={() => handleRename(file.id)}
                  className="flex-1 bg-[#3d3d3d] border border-gray-600 rounded px-1 py-0 text-xs text-white outline-none"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span className="flex-1 truncate">{file.name}</span>
              )}

              <div className="hidden group-hover:flex gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setRenamingId(file.id);
                    setRenameValue(file.name);
                  }}
                  className="text-gray-500 hover:text-white text-xs"
                  title="Rename"
                >
                  ✎
                </button>
                {files.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveFile(file.id);
                    }}
                    className="text-gray-500 hover:text-red-400 text-xs"
                    title="Delete"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

function getTemplate(lang: string): string {
  switch (lang) {
    case 'python':
    case 'python-ds':
      return '# Write your Python code here\n';
    case 'cpp-basic':
      return '#include <iostream>\n\nint main() {\n    std::cout << "Hello Polyglot!" << std::endl;\n    return 0;\n}\n';
    case 'go-sys':
      return 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello Polyglot!")\n}\n';
    case 'node-js':
      return 'console.log("Hello Polyglot!");\n';
    case 'rust-sys':
      return 'fn main() {\n    println!("Hello Polyglot!");\n}\n';
    default:
      return '// Write your code here\n';
  }
}
