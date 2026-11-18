"use client";

import { useQuery, useMutation } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Id } from "../../../../convex/_generated/dataModel";

const statusColors: Record<string, string> = {
  active: "border-primary/30 text-primary",
  trialing: "border-score-amber/30 text-score-amber",
  canceled: "border-destructive/30 text-destructive",
  past_due: "border-destructive/30 text-destructive",
};

export default function AdminUsers() {
  const data = useQuery(api.users.getUsersDashboard);
  const updatePlan = useMutation(api.users.updateUserPlan);

  if (!data) {
    return <p className="font-mono text-muted-foreground">Loading users...</p>;
  }

  const { users, truncated } = data;

  const handlePlanChange = (userId: string, plan: "free" | "pro" | "business") => {
    updatePlan({ userId: userId as Id<"users">, plan });
  };

  return (
    <div className="space-y-4">
      {truncated && (
        <div className="font-mono text-sm text-score-amber bg-score-amber/5 px-3 py-2 rounded-md">
          Results limited to 500 items. Some data may not be displayed.
        </div>
      )}
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">NAME</th>
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">EMAIL</th>
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">PLAN</th>
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">STATUS</th>
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">TASKS</th>
            <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground font-normal">JOINED</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.userId} className="border-b border-border last:border-0 hover:bg-muted/50 transition-colors">
              <td className="px-4 py-3 font-mono text-sm text-foreground">{u.name}</td>
              <td className="px-4 py-3 font-mono text-sm text-muted-foreground">{u.email}</td>
              <td className="px-4 py-3">
                <Select
                  value={u.plan}
                  onValueChange={(val) => handlePlanChange(u.userId, val as "free" | "pro" | "business")}
                >
                  <SelectTrigger className="h-7 font-mono text-xs border-border w-24 bg-card">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[100] border border-border shadow-lg bg-white">
                    <SelectItem value="free" className="font-mono text-xs">free</SelectItem>
                    <SelectItem value="pro" className="font-mono text-xs">pro</SelectItem>
                    <SelectItem value="business" className="font-mono text-xs">business</SelectItem>
                  </SelectContent>
                </Select>
              </td>
              <td className="px-4 py-3">
                <Badge variant="outline" className={`font-mono text-xs ${statusColors[u.subscriptionStatus] ?? ""}`}>
                  {u.subscriptionStatus}
                </Badge>
              </td>
              <td className="px-4 py-3 font-mono text-sm text-foreground">{u.taskCount}</td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                {new Date(u.createdAt).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </div>
  );
}
