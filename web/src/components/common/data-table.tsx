import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";

export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: ReactNode[][];
}) {
  return (
    <Card>
      <CardContent className="overflow-x-auto p-0">
        <Table>
          <thead>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column}>{column}</TableHead>
              ))}
            </TableRow>
          </thead>
          <tbody>
            {rows.map((cells, index) => (
              <TableRow key={index}>
                {cells.map((cell, cellIndex) => (
                  <TableCell key={`${index}-${cellIndex}`}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
          </tbody>
        </Table>
      </CardContent>
    </Card>
  );
}
