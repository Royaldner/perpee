import { useState, useCallback, useEffect } from "react"
import { Outlet } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Sidebar } from "./Sidebar"
import { ChatPanel } from "./ChatPanel"
import { useChat } from "@/hooks/useChat"

export function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { messages, isConnected, isThinking, sendMessage } = useChat()

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      // Mobile: hide sidebar
      if (width < 768) {
        setSidebarCollapsed(true)
        setChatOpen(false)
      }
      // Tablet: collapse sidebar
      else if (width < 1024) {
        setSidebarCollapsed(true)
      }
      // Desktop: show sidebar
      else if (width < 1280) {
        setSidebarCollapsed(false)
        setChatOpen(false)
      }
      // Wide: show both
      else {
        setSidebarCollapsed(false)
      }
    }

    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  const toggleChat = useCallback(() => {
    setChatOpen((prev) => !prev)
  }, [])

  const toggleMobileMenu = useCallback(() => {
    setMobileMenuOpen((prev) => !prev)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile Menu Button */}
      <div className="fixed left-4 top-3 z-50 md:hidden">
        <Button
          variant="outline"
          size="icon"
          onClick={toggleMobileMenu}
        >
          {mobileMenuOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </Button>
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-40 md:relative md:z-auto transition-transform duration-200",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <Sidebar
          collapsed={sidebarCollapsed && !mobileMenuOpen}
          onChatToggle={toggleChat}
          chatOpen={chatOpen}
        />
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="container mx-auto p-4 md:p-6 lg:p-8 pt-14 md:pt-6">
          <Outlet />
        </div>
      </main>

      {/* Chat Panel */}
      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={messages}
        isConnected={isConnected}
        isThinking={isThinking}
        onSend={sendMessage}
      />
    </div>
  )
}
