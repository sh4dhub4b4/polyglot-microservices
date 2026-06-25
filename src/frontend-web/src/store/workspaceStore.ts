import { create } from 'zustand';

export interface FileNode {
  id: string;
  name: string;
  content: string;
  language: string;
}

export type ExecutionState = 'idle' | 'queued' | 'executing' | 'completed' | 'error';

interface WorkspaceState {
  code: string;
  language: string;
  terminalOutput: string[];
  stdin: string;
  executionState: ExecutionState;
  executionError: string | null;
  files: FileNode[];
  activeFileId: string | null;

  setCode: (code: string) => void;
  setLanguage: (lang: string) => void;
  setStdin: (stdin: string) => void;
  appendTerminalOutput: (output: string) => void;
  clearTerminal: () => void;
  setExecutionState: (state: ExecutionState) => void;
  setExecutionError: (error: string | null) => void;
  setFiles: (files: FileNode[]) => void;
  setActiveFileId: (id: string | null) => void;
  addFile: (file: FileNode) => void;
  removeFile: (id: string) => void;
  updateFileContent: (id: string, content: string) => void;
  renameFile: (id: string, name: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  code: '# Write your code here\n',
  language: 'python-ds',
  terminalOutput: [],
  stdin: '',
  executionState: 'idle',
  executionError: null,
  files: [
    { id: 'main', name: 'main.py', content: '// Write your code here\n', language: 'python-ds' },
  ],
  activeFileId: 'main',

  setCode: (code) => set({ code }),
  setLanguage: (language) => set({ language }),
  setStdin: (stdin) => set({ stdin }),
  appendTerminalOutput: (output) => set((state) => ({ terminalOutput: [...state.terminalOutput, output] })),
  clearTerminal: () => set({ terminalOutput: [] }),
  setExecutionState: (executionState) => set({ executionState }),
  setExecutionError: (executionError) => set({ executionError }),
  setFiles: (files) => set({ files }),
  setActiveFileId: (activeFileId) => set((state) => {
    const file = state.files.find((f) => f.id === activeFileId);
    return {
      activeFileId,
      code: file ? file.content : state.code,
      language: file ? file.language : state.language,
    };
  }),
  addFile: (file) => set((state) => ({
    files: [...state.files, file],
    activeFileId: file.id,
    code: file.content,
    language: file.language,
  })),
  removeFile: (id) => set((state) => {
    const remaining = state.files.filter((f) => f.id !== id);
    const wasActive = state.activeFileId === id;
    const nextActive = wasActive ? (remaining[0] || null) : state.files.find((f) => f.id === state.activeFileId) || null;
    return {
      files: remaining,
      activeFileId: nextActive?.id || null,
      code: nextActive?.content || '',
      language: nextActive?.language || 'python',
    };
  }),
  updateFileContent: (id, content) => set((state) => ({
    files: state.files.map((f) => f.id === id ? { ...f, content } : f),
    code: state.activeFileId === id ? content : state.code,
  })),
  renameFile: (id, name) => set((state) => ({
    files: state.files.map((f) => f.id === id ? { ...f, name } : f),
  })),
}));
