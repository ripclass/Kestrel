import type { ActivityEvent } from "@/types/domain";
import { EmptyState } from "@/components/common/empty-state";
import { ActivityTimeline } from "@/components/investigate/activity-timeline";

export function CaseTimeline({ events }: { events: ActivityEvent[] }) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No case activity yet"
        description="Case timeline events will appear here once analysts start working the record."
      />
    );
  }

  return <ActivityTimeline events={events} />;
}
