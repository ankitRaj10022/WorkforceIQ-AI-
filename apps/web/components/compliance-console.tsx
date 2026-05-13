"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import type {
  ComplianceCreateResponse,
  ComplianceListResponse,
} from "@/types/api";

const REQUEST_TYPES = ["DATA_EXPORT", "DATA_DELETION", "RECTIFICATION"];

export function ComplianceConsole() {
  const [payload, setPayload] = useState<ComplianceListResponse | null>(null);
  const [employeeId, setEmployeeId] = useState("EMP-0841");
  const [requestType, setRequestType] = useState("DATA_EXPORT");
  const [reason, setReason] = useState("Employee initiated privacy workflow.");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function loadRequests() {
    const response = await requestJson<ComplianceListResponse>(
      "/api/backend/compliance/requests?limit=25",
    );
    setPayload(response);
  }

  useEffect(() => {
    let active = true;
    requestJson<ComplianceListResponse>("/api/backend/compliance/requests?limit=25")
      .then((response) => {
        if (active) {
          setPayload(response);
          setError(null);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Unable to load compliance requests.",
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function submitRequest() {
    setSubmitting(true);
    setNotice(null);
    setError(null);

    try {
      const response = await requestJson<ComplianceCreateResponse>(
        "/api/backend/compliance/requests",
        {
          method: "POST",
          body: JSON.stringify({
            request_type: requestType,
            employee_id: employeeId,
            reason,
          }),
        },
      );
      setNotice(
        `Compliance request ${response.id} created for ${response.subject_employee_id}.`,
      );
      await loadRequests();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to create compliance request.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Create Request</p>
          <div className="mt-4 grid gap-3">
            <input
              className="field"
              value={employeeId}
              onChange={(event) => setEmployeeId(event.target.value)}
              placeholder="EMP-0841"
            />
            <select
              className="field"
              value={requestType}
              onChange={(event) => setRequestType(event.target.value)}
            >
              {REQUEST_TYPES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <textarea
              className="field min-h-28"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Reason for request"
            />
            <button
              type="button"
              className="button-primary"
              onClick={submitRequest}
              disabled={submitting}
            >
              {submitting ? "Submitting..." : "Create Compliance Request"}
            </button>
            {notice ? (
              <div className="rounded-2xl border border-success/20 bg-success/8 px-4 py-3 text-sm text-success">
                {notice}
              </div>
            ) : null}
            {error ? (
              <div className="rounded-2xl border border-danger/20 bg-danger/8 px-4 py-3 text-sm text-danger">
                {error}
              </div>
            ) : null}
          </div>
        </article>

        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Recent Requests</p>
          <div className="table-shell mt-4">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Employee</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {payload?.requests?.map((request) => (
                  <tr key={request.id}>
                    <td className="mono">{request.id}</td>
                    <td>{request.request_type}</td>
                    <td>{request.subject_employee_id}</td>
                    <td>{request.status}</td>
                    <td>{formatDateTime(request.created_at)}</td>
                  </tr>
                )) ?? (
                  <tr>
                    <td colSpan={5} className="text-sm text-muted">
                      Loading compliance requests...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  );
}
