"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import type { EmployeeSearchResponse } from "@/types/api";

export function EmployeeDirectory() {
  const [query, setQuery] = useState("Priya");
  const deferredQuery = useDeferredValue(query);
  const [payload, setPayload] = useState<EmployeeSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const normalized = deferredQuery.trim();
    if (normalized.length < 2) {
      return;
    }

    let active = true;
    requestJson<EmployeeSearchResponse>(
      `/api/backend/search/employees?q=${encodeURIComponent(normalized)}&limit=12`,
    )
      .then((response) => {
        if (!active) {
          return;
        }
        setPayload(response);
        setError(null);
      })
      .catch((cause) => {
        if (!active) {
          return;
        }
        setError(
          cause instanceof Error ? cause.message : "Unable to search employees.",
        );
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [deferredQuery]);

  return (
    <div className="grid gap-5">
      <section className="panel rounded-[1.5rem] p-5">
        <p className="eyebrow">Employee Search</p>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto]">
          <input
            className="field"
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              if (nextQuery.trim().length < 2) {
                setPayload(null);
                setError(null);
                setLoading(false);
              } else {
                setLoading(true);
              }
            }}
            placeholder="Search by employee ID, name, department, role, or email"
          />
          <div className="rounded-2xl border border-border bg-white/74 px-4 py-3 text-sm text-muted">
            Backend: {payload?.backend ?? "waiting"}
          </div>
        </div>
        <p className="mt-3 text-sm text-muted">
          Search resolves through the backend RBAC rules, not direct database
          access.
        </p>
      </section>

      {error ? (
        <div className="rounded-[1.5rem] border border-danger/20 bg-danger/8 px-4 py-4 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="panel rounded-[1.5rem] p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Results</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
              Workforce directory
            </h2>
          </div>
          {loading ? <p className="text-sm text-muted">Searching...</p> : null}
        </div>

        {payload?.results?.length ? (
          <div className="table-shell mt-5">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {payload.results.map((employee) => (
                  <tr key={employee.employee_id}>
                    <td>
                      <div className="font-semibold">{employee.name}</div>
                      <div className="mono text-xs text-muted">
                        {employee.employee_id}
                      </div>
                    </td>
                    <td>{employee.department}</td>
                    <td>{employee.role}</td>
                    <td>{employee.status}</td>
                    <td>{employee.performance_score ?? "N/A"}</td>
                    <td>
                      <Link
                        href={`/portal/employees/${employee.employee_id}`}
                        className="button-secondary"
                      >
                        Open Profile
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-5 rounded-2xl border border-dashed border-border px-4 py-8 text-sm text-muted">
            {payload?.suggestion ??
              "Type at least two characters to start searching the workforce directory."}
          </div>
        )}
      </section>
    </div>
  );
}
