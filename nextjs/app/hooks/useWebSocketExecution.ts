/**
 * WebSocket Code Execution Hook
 *
 * Handles real-time code execution with interactive input/output via WebSocket
 */

import { useState, useRef, useCallback } from 'react';
import { createJob, JobApiError } from '../lib/api/jobApi';

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

    try {
      // Step 1: Create job and get token (no API key needed - handled server-side)
      addOutputLine('system', 'Creating execution job...');

      let jobData;
      try {
        jobData = await createJob();
      } catch (error) {
        if (error instanceof JobApiError) {
          addOutputLine('stderr', `Failed to create job: ${error.message}`);
        } else {
          addOutputLine('stderr', 'Unexpected error creating job');
        }
        setIsExecuting(false);
        return;
      }

      const { job_id, job_token, expires_at } = jobData;
      addOutputLine('system', `Job created: ${job_id}`);
      addOutputLine('system', `Token expires: ${new Date(expires_at).toLocaleTimeString()}`);

      // Step 2: Connect to WebSocket
      addOutputLine('system', 'Connecting to execution service...');

      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/execute';

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Connection opened
      ws.onopen = () => {
        addOutputLine('system', 'Connected! Authenticating and starting execution...');

        // Step 3: Send authenticated execution request
        // IMPORTANT: No API key here, only job_id and job_token
        ws.send(JSON.stringify({
          type: 'execute',
          job_id,
          job_token,
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
        // Code 1008 indicates authentication failure
        if (event.code === 1008) {
          addOutputLine('stderr', 'Authentication failed - invalid or expired token');
        } else if (isExecuting) {
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
