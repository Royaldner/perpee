import { useState, useCallback, type KeyboardEvent } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Type a message...",
}: ChatInputProps) {
  const [message, setMessage] = useState("")

  const handleSend = useCallback(() => {
    const trimmed = message.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setMessage("")
    }
  }, [message, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <div className="flex gap-2">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1"
        autoComplete="off"
      />
      <Button
        size="icon"
        onClick={handleSend}
        disabled={disabled || !message.trim()}
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}
