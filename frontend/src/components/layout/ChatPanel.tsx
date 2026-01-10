import { useRef, useEffect } from "react"
import { X, Minimize2, Maximize2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChatInput } from "@/components/chat/ChatInput"
import { ChatMessage } from "@/components/chat/ChatMessage"
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator"
import type { WebSocketMessage } from "@/types/api"

interface ChatPanelProps {
  open: boolean
  onClose: () => void
  messages: WebSocketMessage[]
  isConnected: boolean
  isThinking: boolean
  onSend: (message: string) => void
  minimized?: boolean
  onMinimize?: () => void
}

export function ChatPanel({
  open,
  onClose,
  messages,
  isConnected,
  isThinking,
  onSend,
  minimized = false,
  onMinimize,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isThinking])

  if (!open) return null

  return (
    <aside
      className={cn(
        "flex flex-col border-l bg-card transition-all duration-200",
        minimized ? "w-80" : "w-96"
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "h-2 w-2 rounded-full",
              isConnected ? "bg-green-500" : "bg-red-500"
            )}
          />
          <span className="font-semibold">Chat with Perpee</span>
        </div>
        <div className="flex items-center gap-1">
          {onMinimize && (
            <Button variant="ghost" size="icon" onClick={onMinimize}>
              {minimized ? (
                <Maximize2 className="h-4 w-4" />
              ) : (
                <Minimize2 className="h-4 w-4" />
              )}
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <p className="text-sm">Welcome to Perpee!</p>
              <p className="text-xs mt-1">
                Ask me to track a product, check prices, or set up alerts.
              </p>
            </div>
          )}
          {messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))}
          {isThinking && <ThinkingIndicator />}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t p-4">
        <ChatInput
          onSend={onSend}
          disabled={!isConnected || isThinking}
          placeholder={
            !isConnected
              ? "Connecting..."
              : isThinking
                ? "Thinking..."
                : "Ask Perpee anything..."
          }
        />
      </div>
    </aside>
  )
}
