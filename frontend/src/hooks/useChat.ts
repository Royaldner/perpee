/**
 * React hook for WebSocket chat with the Perpee agent.
 */

import { useState, useEffect, useCallback, useRef } from "react"
import {
  ChatWebSocket,
  getChatWebSocket,
  type ConnectionStatus,
} from "@/lib/websocket"
import type { WebSocketMessage } from "@/types/api"

interface UseChatReturn {
  messages: WebSocketMessage[]
  isConnected: boolean
  isThinking: boolean
  status: ConnectionStatus
  sendMessage: (content: string) => void
  clearMessages: () => void
  connect: () => void
  disconnect: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>("disconnected")
  const [isThinking, setIsThinking] = useState(false)
  const wsRef = useRef<ChatWebSocket | null>(null)

  // Initialize WebSocket on mount
  useEffect(() => {
    const ws = getChatWebSocket({
      onMessage: (message) => {
        // Handle different message types
        switch (message.type) {
          case "welcome":
            // Don't add welcome messages to the chat history
            break
          case "thinking":
            setIsThinking(true)
            break
          case "tool_call":
          case "tool_result":
            // Add tool messages for display
            setMessages((prev) => [...prev, message])
            break
          case "response":
            setIsThinking(false)
            setMessages((prev) => [...prev, message])
            break
          case "error":
            setIsThinking(false)
            setMessages((prev) => [...prev, message])
            break
          default:
            setMessages((prev) => [...prev, message])
        }
      },
      onStatusChange: setStatus,
    })

    wsRef.current = ws
    ws.connect()

    return () => {
      ws.disconnect()
    }
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || !content.trim()) return

    // Add user message to chat history
    const userMessage: WebSocketMessage = {
      type: "message",
      data: { content },
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsThinking(true)

    // Send to server
    wsRef.current.send(content)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  const connect = useCallback(() => {
    wsRef.current?.connect()
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect()
  }, [])

  return {
    messages,
    isConnected: status === "connected",
    isThinking,
    status,
    sendMessage,
    clearMessages,
    connect,
    disconnect,
  }
}
