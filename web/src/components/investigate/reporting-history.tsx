import { Currency } from "@/components/common/currency";
import { RelativeTime } from "@/components/common/relative-time";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/table";
import type { ReportingHistoryItem } from "@/types/domain";

export function ReportingHistory({ history }: { history: ReportingHistoryItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Reporting history</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <Table>
          <thead>
            <TableRow>
              <TableHead>Reporting org</TableHead>
              <TableHead>Reference</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Exposure</TableHead>
              <TableHead>When</TableHead>
            </TableRow>
          </thead>
          <tbody>
            {history.map((item) => (
              <TableRow key={item.reportRef}>
                <TableCell>{item.orgName}</TableCell>
                <TableCell>{item.reportRef}</TableCell>
                <TableCell>{item.channel}</TableCell>
                <TableCell><Currency amount={item.amount} /></TableCell>
                <TableCell><RelativeTime value={item.reportedAt} /></TableCell>
              </TableRow>
            ))}
          </tbody>
        </Table>
      </CardContent>
    </Card>
  );
}
