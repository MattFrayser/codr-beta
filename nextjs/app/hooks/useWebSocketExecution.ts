/**
 * WebSocket Code Execution Hook
 *
 * Handles real-time code execution with interactive input/output via WebSocket
 */

import { useState, useRef, useCallback } from 'react';

export interface OutputLine {
  type: 'stdout' | 'stderr' | 'system' | 'input';
  content: string;
  timestamp?: number;
}

export interface UseWebSocketExecutionResult {
  outputLines: OutputLine[];
  isExecuting: boolean;
  execute: (code: string, language: string) => Promise<void>;
  sendInput: (input: string) => void;
  clearOutput: () => void;
}

export function useWebSocketExecution(): UseWebSocketExecutionResult {
  const [outputLines, setOutputLines] = useState<OutputLine[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  /**
   * Add output line to the display
   */
  const addOutputLine = useCallback((type: OutputLine['type'], content: string) => {
    setOutputLines(prev => [
      ...prev,
      { type, content, timestamp: Date.now() }
    ]);
  }, []);

  /**
   * Send user input to PTY - industry standard approach
   */
  const sendInput = useCallback((input: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Send input directly to PTY (type changed from 'input_response' to 'input')
      wsRef.current.send(JSON.stringify({
        type: 'input',
        data: input + '\n'
      }));

      // Add user input to output display
      addOutputLine('input', input);
    }
  }, [addOutputLine]);

  /**
   * Execute code via WebSocket
   */
  const execute = useCallback(async (code: string, language: string): Promise<void> => {
    if (!code.trim()) {
      addOutputLine('system', 'Please enter some code');
      return;
    }

    // Clear previous output
    setOutputLines([]);
    setIsExecuting(true);
    addOutputLine('system', 'Connecting to execution service...');

    try {
      // Determine WebSocket protocol based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;

      // For development, connect directly to backend
      const isDev = process.env.NODE_ENV === 'development';
      const wsUrl = isDev
        ? 'ws://localhost:8000/ws/execute'
        : `${protocol}//${host}/ws/execute`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Connection opened
      ws.onopen = () => {
        addOutputLine('system', 'Connected! Starting execution...');

        // Send execute message
        ws.send(JSON.stringify({
          type: 'execute',
          api_key: process.env.NEXT_PUBLIC_API_KEY,
          code,
          language
        }));
      };

      // Handle incoming messages
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'output':
              // Real-time output from PTY
              const stream = message.stream as 'stdout' | 'stderr';
              addOutputLine(stream, message.data);
              break;

            case 'complete':
              // Execution completed
              addOutputLine('system', `\nExecution completed in ${message.execution_time?.toFixed(3)}s (exit code: ${message.exit_code})`);
              setIsExecuting(false);
              ws.close();
              break;

            case 'error':
              // Error occurred
              addOutputLine('stderr', `Error: ${message.message}`);
              setIsExecuting(false);
              ws.close();
              break;

            default:
              console.warn('Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          addOutputLine('system', 'Error parsing server message');
        }
      };

      // Handle errors
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addOutputLine('system', 'Connection error - please check your connection');
        setIsExecuting(false);
      };

      // Handle connection close
      ws.onclose = (event) => {
        if (isExecuting) {
          if (event.wasClean) {
            console.log(`WebSocket closed cleanly, code=${event.code}, reason=${event.reason}`);
          } else {
            addOutputLine('system', 'Connection lost unexpectedly');
          }
        }
        setIsExecuting(false);
        wsRef.current = null;
      };

    } catch (err: any) {
      addOutputLine('system', `Failed to connect: ${err.message}`);
      setIsExecuting(false);
    }
  }, [addOutputLine, isExecuting]);

  /**
   * Clear all output
   */
  const clearOutput = useCallback(() => {
    setOutputLines([]);

    // Close WebSocket if open
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return {
    outputLines,
    isExecuting,
    execute,
    sendInput,
    clearOutput
  };
}
