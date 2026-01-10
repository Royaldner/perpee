import { useMemo } from "react"
import DOMPurify from "dompurify"
import { User, Bot, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { ToolCallDisplay } from "./ToolCallDisplay"
import type {
  WebSocketMessage,
  ResponseData,
  ToolCallData,
  ToolResultData,
  ErrorData,
} from "@/types/api"

interface ChatMessageProps {
  message: WebSocketMessage
  className?: string
}

export function ChatMessage({ message, className }: ChatMessageProps) {
  // Sanitize content for XSS prevention
  const sanitizedContent = useMemo(() => {
    if (message.type === "message") {
      return DOMPurify.sanitize(String(message.data.content || ""))
    }
    if (message.type === "response") {
      const data = message.data as unknown as ResponseData
      return DOMPurify.sanitize(data.content || "")
    }
    if (message.type === "error") {
      const data = message.data as unknown as ErrorData
      return DOMPurify.sanitize(data.message || "An error occurred")
    }
    return ""
  }, [message])

  // User message
  if (message.type === "message") {
    return (
      <div className={cn("flex gap-3", className)}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <User className="h-4 w-4" />
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium">You</p>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p>{sanitizedContent}</p>
          </div>
        </div>
      </div>
    )
  }

  // Agent response
  if (message.type === "response") {
    const data = message.data as unknown as ResponseData
    return (
      <div className={cn("flex gap-3", className)}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-periwinkle-500 text-white">
          <Bot className="h-4 w-4" />
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-periwinkle-600 dark:text-periwinkle-400">
            Perpee
          </p>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            {/* Render markdown-style content */}
            {sanitizedContent.split("\n").map((line, i) => (
              <p key={i} className={line ? "" : "h-4"}>
                {line}
              </p>
            ))}
          </div>
          {/* Show tool calls if any */}
          {data.tool_calls && data.tool_calls.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {data.tool_calls.map((tc, i) => (
                <ToolCallDisplay
                  key={i}
                  toolCall={tc}
                  result={{ tool_name: tc.tool_name, success: true, result: null, error: null }}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Tool call notification
  if (message.type === "tool_call") {
    const data = message.data as unknown as ToolCallData
    return (
      <div className={cn("ml-11", className)}>
        <ToolCallDisplay toolCall={data} />
      </div>
    )
  }

  // Tool result notification
  if (message.type === "tool_result") {
    const data = message.data as unknown as ToolResultData
    return (
      <div className={cn("ml-11", className)}>
        <ToolCallDisplay
          toolCall={{ tool_name: data.tool_name, tool_args: {} }}
          result={data}
        />
      </div>
    )
  }

  // Error message
  if (message.type === "error") {
    return (
      <div className={cn("flex gap-3", className)}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-destructive text-destructive-foreground">
          <AlertCircle className="h-4 w-4" />
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-destructive">Error</p>
          <p className="text-sm text-muted-foreground">{sanitizedContent}</p>
        </div>
      </div>
    )
  }

  return null
}
