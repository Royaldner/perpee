import { useQuery } from "@tanstack/react-query"
import { Sun, Moon, Monitor, Info, Heart } from "lucide-react"
import { healthApi } from "@/lib/api"
import { useTheme } from "@/hooks/useTheme"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"

export function Settings() {
  const { theme, setTheme } = useTheme()

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => healthApi.check(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Configure your Perpee experience"
      />

      {/* Theme Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>
            Customize how Perpee looks on your device
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Theme</Label>
            <div className="flex gap-2">
              <Button
                variant={theme === "light" ? "default" : "outline"}
                onClick={() => setTheme("light")}
                className="flex-1"
              >
                <Sun className="mr-2 h-4 w-4" />
                Light
              </Button>
              <Button
                variant={theme === "dark" ? "default" : "outline"}
                onClick={() => setTheme("dark")}
                className="flex-1"
              >
                <Moon className="mr-2 h-4 w-4" />
                Dark
              </Button>
              <Button
                variant={theme === "system" ? "default" : "outline"}
                onClick={() => setTheme("system")}
                className="flex-1"
              >
                <Monitor className="mr-2 h-4 w-4" />
                System
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Select your preferred theme or use your system settings
            </p>
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
          <CardDescription>
            Current health of Perpee services
          </CardDescription>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span>Overall Status</span>
                <Badge
                  variant={
                    health?.status === "healthy"
                      ? "success"
                      : health?.status === "degraded"
                        ? "warning"
                        : "destructive"
                  }
                >
                  {health?.status ?? "Unknown"}
                </Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span>Database</span>
                <Badge variant={health?.database ? "success" : "destructive"}>
                  {health?.database ? "Connected" : "Disconnected"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Vector DB (ChromaDB)</span>
                <Badge variant={health?.chromadb ? "success" : "destructive"}>
                  {health?.chromadb ? "Connected" : "Disconnected"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Scheduler</span>
                <Badge variant={health?.scheduler ? "success" : "destructive"}>
                  {health?.scheduler ? "Running" : "Stopped"}
                </Badge>
              </div>
              {health?.version && (
                <>
                  <Separator />
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Version</span>
                    <span>{health.version}</span>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle>About Perpee</CardTitle>
          <CardDescription>
            AI-powered price monitoring for Canadian online retailers
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3 p-4 rounded-lg bg-muted">
            <Info className="h-5 w-5 mt-0.5 text-primary" />
            <div className="space-y-1">
              <p className="text-sm font-medium">How it works</p>
              <p className="text-sm text-muted-foreground">
                Perpee automatically monitors prices across 16+ Canadian retailers.
                Add products via URL or natural language chat, set up alerts,
                and get notified via email when prices drop.
              </p>
            </div>
          </div>

          <div className="space-y-2 text-sm">
            <p><strong>Supported Stores:</strong></p>
            <p className="text-muted-foreground">
              Amazon Canada, Walmart Canada, Best Buy Canada, Costco, Canadian Tire,
              Memory Express, Canada Computers, Newegg Canada, Loblaws, No Frills,
              Real Canadian Superstore, Metro, Sobeys, Shoppers Drug Mart, Home Depot Canada,
              The Source
            </p>
          </div>

          <Separator />

          <div className="flex items-center justify-center gap-1 text-sm text-muted-foreground">
            Made with <Heart className="h-4 w-4 text-red-500" /> for Canadian shoppers
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
