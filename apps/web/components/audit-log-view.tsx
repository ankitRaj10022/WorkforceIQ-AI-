"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type { AuditLogResponse } from "@/types/api";

export function AuditLogView() {
  const [payload, setPayload] = useState<AuditLogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    requestJson<AuditLogResponse>("/api/backend/audit-logs?limit=50")
      .then((response) => {
        if (active) {
          setPayload(response);
          setError(null);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to load audit logs.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-[1.5rem] border border-danger/20 bg-danger/8 px-4 py-4 text-sm text-danger">
        {error}
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <section className="panel rounded-[1.5rem] p-5">
        <p className="eyebrow">Audit Trail</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
          Access-sensitive event history
        </h2>
      </section>
      <section className="panel rounded-[1.5rem] p-5">
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Action</th>
                <th>Entity</th>
                <th>Target</th>
                <th>Timestamp</th>
                <th>Request ID</th>
              </tr>
            </thead>
            <tbody>
              {payload?.audit_logs?.map((log) => (
                <tr key={log.id}>
                  <td>{log.action}</td>
                  <td>{log.target_entity}</td>
                  <td className="mono">{log.target_id}</td>
                  <td>{formatDateTime(log.timestamp)}</td>
                  <td className="mono text-xs">{log.request_id}</td>
                </tr>
              )) ?? (
                <tr>
                  <td colSpan={5} className="text-sm text-muted">
                    Loading audit logs...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
