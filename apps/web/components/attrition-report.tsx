"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { AttritionReportResponse } from "@/types/api";

export function AttritionReport() {
  const [limit, setLimit] = useState(10);
  const [payload, setPayload] = useState<AttritionReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    requestJson<AttritionReportResponse>(
      `/api/backend/reports/attrition-risk?limit=${limit}`,
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
        setError(cause instanceof Error ? cause.message : "Unable to load report.");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [limit]);

  return (
    <div className="grid gap-5">
      <section className="panel rounded-[1.5rem] p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Attrition Report</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
              Workforce risk concentration
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted" htmlFor="limit">
              Row limit
            </label>
            <input
              id="limit"
              className="field w-28"
              type="number"
              min={1}
              max={100}
              value={limit}
              onChange={(event) => {
                setLoading(true);
                setLimit(Number(event.target.value || 10));
              }}
            />
          </div>
        </div>
      </section>

      {loading ? (
        <div className="panel rounded-[1.5rem] p-5 text-sm text-muted">
          Loading attrition report...
        </div>
      ) : null}

      {error ? (
        <div className="rounded-[1.5rem] border border-danger/20 bg-danger/8 px-4 py-4 text-sm text-danger">
          {error}
        </div>
      ) : null}

      {payload ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {payload.executive_summary.map((summary) => (
              <article key={summary} className="panel rounded-[1.5rem] p-5">
                <p className="text-sm leading-6 text-muted">{summary}</p>
              </article>
            ))}
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Estimated Cost</p>
              <p className="metric mt-4 text-3xl font-semibold">
                {formatCurrency(payload.financial_exposure.total_estimated_cost)}
              </p>
              <p className="mt-2 text-sm text-muted">
                Generated {formatDateTime(payload.generated_at)}
              </p>
            </article>
          </section>

          <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Department Distribution</p>
              <div className="mt-4 grid gap-3">
                {Object.entries(payload.grouped_by_department).map(
                  ([department, counts]) => (
                    <div
                      key={department}
                      className="rounded-2xl border border-border bg-white/68 px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold">{department}</p>
                        <span className="badge badge-neutral">
                          H {counts.HIGH} · M {counts.MEDIUM} · L {counts.LOW}
                        </span>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </article>

            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">High-Risk Cases</p>
              <div className="table-shell mt-4">
                <table>
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Probability</th>
                      <th>Confidence</th>
                      <th>Estimated Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payload.high_risk_employees.map((employee) => (
                      <tr key={employee.employee_id}>
                        <td>
                          <div className="font-semibold">{employee.employee_name}</div>
                          <div className="text-xs text-muted">{employee.department}</div>
                        </td>
                        <td>{Math.round(employee.predicted_attrition_probability * 100)}%</td>
                        <td>{Math.round(employee.confidence * 100)}%</td>
                        <td>{formatCurrency(employee.estimated_replacement_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}
