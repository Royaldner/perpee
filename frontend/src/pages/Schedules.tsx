import { useSearchParams, Link } from "react-router-dom"
import { Calendar, Pause, Play, Trash2 } from "lucide-react"
import { formatDate, formatRelativeTime } from "@/lib/utils"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useSchedules,
  useDeleteSchedule,
  useUpdateSchedule,
} from "@/hooks/useSchedules"

export function Schedules() {
  const [searchParams, setSearchParams] = useSearchParams()
  const isActive = searchParams.get("is_active")

  const { data: schedulesData, isLoading } = useSchedules({
    is_active: isActive === "true" ? true : isActive === "false" ? false : undefined,
  })

  const deleteSchedule = useDeleteSchedule()
  const updateSchedule = useUpdateSchedule()

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this schedule?")) {
      await deleteSchedule.mutateAsync(id)
    }
  }

  const handleToggle = async (id: number, isActive: boolean) => {
    await updateSchedule.mutateAsync({ id, data: { is_active: !isActive } })
  }

  const handleActiveFilter = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value === "all") {
      newParams.delete("is_active")
    } else {
      newParams.set("is_active", value)
    }
    setSearchParams(newParams)
  }

  // Parse cron expression to human-readable text
  const parseCron = (cron: string): string => {
    // Simple parsing for common patterns
    if (cron === "0 6 * * *") return "Daily at 6:00 AM"
    if (cron === "0 0 * * *") return "Daily at midnight"
    if (cron.match(/^0 \d+ \* \* \*$/)) {
      const hour = parseInt(cron.split(" ")[1], 10)
      return `Daily at ${hour}:00`
    }
    return cron
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Schedules"
        description="Manage price check schedules"
      />

      {/* Info Card */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">
            Schedules determine when products are checked for price changes. By default,
            all products are checked daily at 6:00 AM. You can create custom schedules
            for specific products or stores.
          </p>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex gap-4">
        <Select
          value={isActive ?? "all"}
          onValueChange={handleActiveFilter}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="true">Active</SelectItem>
            <SelectItem value="false">Paused</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Schedules List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : schedulesData?.items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Calendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>No custom schedules found.</p>
          <p className="text-sm mt-1">
            Products are checked daily by default.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {schedulesData?.items.map((schedule) => (
            <Card key={schedule.id}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Calendar className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {schedule.product_name ? (
                        <Link
                          to={`/products/${schedule.product_id}`}
                          className="font-medium hover:underline truncate"
                        >
                          {schedule.product_name}
                        </Link>
                      ) : schedule.store_name ? (
                        <span className="font-medium">{schedule.store_name}</span>
                      ) : (
                        <span className="font-medium">System Schedule</span>
                      )}
                      <Badge variant="outline">
                        {parseCron(schedule.cron_expression)}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {schedule.last_run_at && (
                        <>Last run: {formatRelativeTime(schedule.last_run_at)}</>
                      )}
                      {schedule.next_run_at && (
                        <> · Next: {formatDate(schedule.next_run_at)}</>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge
                      variant={schedule.is_active ? "success" : "secondary"}
                    >
                      {schedule.is_active ? "Active" : "Paused"}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleToggle(schedule.id, schedule.is_active)}
                    >
                      {schedule.is_active ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleDelete(schedule.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
