import { formatRelativeTime } from "@/lib/utils";

export function RelativeTime({ value }: { value: string }) {
  return <span>{formatRelativeTime(value)}</span>;
}
