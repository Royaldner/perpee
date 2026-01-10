import { CheckCircle, XCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ToolCallData, ToolResultData } from "@/types/api"

interface ToolCallDisplayProps {
  toolCall: ToolCallData
  result?: ToolResultData
  className?: string
}

// Human-friendly tool names
const toolNameMap: Record<string, string> = {
  scrape_product: "Fetching product",
  scan_website: "Analyzing website",
  search_products: "Searching products",
  web_search: "Searching the web",
  get_price_history: "Getting price history",
  create_schedule: "Creating schedule",
  set_alert: "Setting alert",
  compare_prices: "Comparing prices",
  list_products: "Listing products",
  remove_product: "Removing product",
}

function getToolDisplayName(toolName: string): string {
  return toolNameMap[toolName] || toolName.replace(/_/g, " ")
}

export function ToolCallDisplay({
  toolCall,
  result,
  className,
}: ToolCallDisplayProps) {
  const displayName = getToolDisplayName(toolCall.tool_name)
  const isLoading = !result
  const isSuccess = result?.success === true
  const isError = result?.success === false

  // Safely get tool args
  const urlArg = toolCall.tool_args.url
  const queryArg = toolCall.tool_args.query

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground py-1 px-2 rounded-md bg-muted/50",
        className
      )}
    >
      {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {isSuccess && <CheckCircle className="h-3.5 w-3.5 text-green-500" />}
      {isError && <XCircle className="h-3.5 w-3.5 text-red-500" />}

      <span className="capitalize">{displayName}</span>

      {/* Show tool arguments if relevant */}
      {typeof urlArg === "string" && urlArg && (
        <span className="text-xs opacity-70 truncate max-w-[150px]">
          ({String(urlArg).split("/").pop()})
        </span>
      )}
      {typeof queryArg === "string" && queryArg && (
        <span className="text-xs opacity-70 truncate max-w-[150px]">
          ("{String(queryArg)}")
        </span>
      )}

      {/* Show error if present */}
      {isError && result?.error && (
        <span className="text-xs text-red-500 truncate max-w-[150px]">
          - {result.error}
        </span>
      )}
    </div>
  )
}
