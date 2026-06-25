import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { useWorkspaceStore } from '../store/workspaceStore';

interface TerminalProps {
  onInput?: (data: string) => void;
}

export const Terminal: React.FC<TerminalProps> = ({ onInput }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#f5f5f5',
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    term.onData((data) => {
      if (onInput) {
        onInput(data);
      }
    });

    xtermRef.current = term;

    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    // Subscribe to store
    const unsubscribe = useWorkspaceStore.subscribe((state, prevState) => {
      const outputs = state.terminalOutput;
      const prevOutputs = prevState.terminalOutput;
      if (outputs.length === 0) {
        term.clear();
      } else if (outputs.length > prevOutputs.length) {
        const newOutputs = outputs.slice(prevOutputs.length);
        newOutputs.forEach(out => term.write(out));
      }
    });

    return () => {
      unsubscribe();
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, [onInput]);
  
  return (
    <div className="w-full h-full bg-[#1e1e1e] p-2 rounded-md overflow-hidden">
      <div ref={terminalRef} className="w-full h-full" />
    </div>
  );
};
