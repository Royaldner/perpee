import { cn } from "@/lib/utils"

interface ThinkingIndicatorProps {
  className?: string
}

export function ThinkingIndicator({ className }: ThinkingIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-2 text-muted-foreground", className)}>
      <div className="flex gap-1">
        <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.3s]" />
        <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.15s]" />
        <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce" />
      </div>
      <span className="text-sm">Perpee is thinking...</span>
    </div>
  )
}
