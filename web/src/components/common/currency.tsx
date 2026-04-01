import { formatBDT } from "@/lib/utils";

export function Currency({ amount }: { amount: number }) {
  return <span>{formatBDT(amount)}</span>;
}
