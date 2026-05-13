"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { DepartmentHealthResponse } from "@/types/api";

export function DepartmentHealthPanel() {
  const [departmentId, setDepartmentId] = useState("1");
  const [activeDepartmentId, setActiveDepartmentId] = useState("1");
  const [payload, setPayload] = useState<DepartmentHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    requestJson<DepartmentHealthResponse>(
      `/api/backend/departments/${activeDepartmentId}/health`,
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
          cause instanceof Error
            ? cause.message
            : "Unable to load department health.",
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
  }, [activeDepartmentId]);

  return (
    <div className="grid gap-5">
      <section className="panel rounded-[1.5rem] p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Department Health</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
              Operational health by department ID
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <input
              className="field w-28"
              value={departmentId}
              onChange={(event) => setDepartmentId(event.target.value)}
              placeholder="1"
            />
            <button
              type="button"
              className="button-primary"
              onClick={() => {
                setLoading(true);
                setActiveDepartmentId(departmentId);
              }}
            >
              Load
            </button>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="panel rounded-[1.5rem] p-5 text-sm text-muted">
          Loading department health...
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
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Department</p>
              <p className="mt-4 text-2xl font-semibold">
                {payload.department.name}
              </p>
              <p className="mt-2 text-sm text-muted">
                Budget {formatCurrency(payload.department.budget)}
              </p>
            </article>
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Headcount Ratio</p>
              <p className="metric mt-4 text-3xl font-semibold">
                {payload.headcount.ratio ?? "N/A"}
              </p>
              <p className="mt-2 text-sm text-muted">
                {payload.headcount.active_count} active /{" "}
                {payload.headcount.target ?? "N/A"} target
              </p>
            </article>
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Performance Average</p>
              <p className="metric mt-4 text-3xl font-semibold">
                {payload.performance.department_average ?? "N/A"}
              </p>
              <p className="mt-2 text-sm text-muted">
                Company benchmark {payload.performance.company_benchmark ?? "N/A"}
              </p>
            </article>
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Health Rating</p>
              <p className="mt-4 text-2xl font-semibold">
                {payload.traffic_light_health.label}
              </p>
              <p className="mt-2 text-sm text-muted">
                Score {payload.traffic_light_health.score} ·{" "}
                {payload.traffic_light_health.indicator}
              </p>
            </article>
          </section>

          <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Executive Summary</p>
              <div className="mt-4 grid gap-3">
                {payload.executive_summary.map((line) => (
                  <div
                    key={line}
                    className="rounded-2xl border border-border bg-white/68 px-4 py-3 text-sm"
                  >
                    {line}
                  </div>
                ))}
              </div>
            </article>

            <article className="panel rounded-[1.5rem] p-5">
              <p className="eyebrow">Risk Reasons</p>
              <div className="mt-4 grid gap-3">
                {payload.traffic_light_health.reasons.length ? (
                  payload.traffic_light_health.reasons.map((reason) => (
                    <div
                      key={reason}
                      className="rounded-2xl border border-border bg-white/68 px-4 py-3 text-sm text-muted"
                    >
                      {reason}
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-border bg-white/68 px-4 py-3 text-sm text-muted">
                    No major risk reasons were returned.
                  </div>
                )}
              </div>
              <p className="mt-4 text-sm text-muted">
                Generated {formatDateTime(payload.generated_at)}
              </p>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}
