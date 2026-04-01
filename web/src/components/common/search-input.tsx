"use client";

import type { ComponentProps } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

export function SearchInput(props: ComponentProps<typeof Input>) {
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input className="pl-10" {...props} />
    </div>
  );
}
