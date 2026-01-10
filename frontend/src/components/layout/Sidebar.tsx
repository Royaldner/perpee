import { Link, useLocation } from "react-router-dom"
import {
  Home,
  Package,
  Bell,
  Calendar,
  Store,
  Settings,
  MessageSquare,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface SidebarProps {
  collapsed?: boolean
  onChatToggle?: () => void
  chatOpen?: boolean
}

const navItems = [
  { path: "/", icon: Home, label: "Dashboard" },
  { path: "/products", icon: Package, label: "Products" },
  { path: "/alerts", icon: Bell, label: "Alerts" },
  { path: "/schedules", icon: Calendar, label: "Schedules" },
  { path: "/stores", icon: Store, label: "Stores" },
  { path: "/settings", icon: Settings, label: "Settings" },
]

export function Sidebar({ collapsed = false, onChatToggle, chatOpen }: SidebarProps) {
  const location = useLocation()

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r bg-card transition-all duration-200",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b px-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
            P
          </div>
          {!collapsed && (
            <span className="text-lg font-semibold">Perpee</span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path

          if (collapsed) {
            return (
              <Tooltip key={item.path}>
                <TooltipTrigger asChild>
                  <Link to={item.path}>
                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      size="icon"
                      className="w-full"
                    >
                      <Icon className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            )
          }

          return (
            <Link key={item.path} to={item.path}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className="w-full justify-start gap-3"
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Button>
            </Link>
          )
        })}
      </nav>

      {/* Chat Toggle */}
      <div className="border-t p-2">
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={chatOpen ? "secondary" : "ghost"}
                size="icon"
                className="w-full"
                onClick={onChatToggle}
              >
                <MessageSquare className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Chat with Perpee</TooltipContent>
          </Tooltip>
        ) : (
          <Button
            variant={chatOpen ? "secondary" : "ghost"}
            className="w-full justify-start gap-3"
            onClick={onChatToggle}
          >
            <MessageSquare className="h-5 w-5" />
            Chat with Perpee
          </Button>
        )}
      </div>
    </aside>
  )
}
