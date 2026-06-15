import { create } from 'zustand';

interface WorkspaceState {
  code: string;
  language: string;
  terminalOutput: string[];
  setCode: (code: string) => void;
  setLanguage: (lang: string) => void;
  appendTerminalOutput: (output: string) => void;
  clearTerminal: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  code: '// Write your code here\n',
  language: 'python',
  terminalOutput: [],
  setCode: (code) => set({ code }),
  setLanguage: (language) => set({ language }),
  appendTerminalOutput: (output) => set((state) => ({ terminalOutput: [...state.terminalOutput, output] })),
  clearTerminal: () => set({ terminalOutput: [] }),
}));
