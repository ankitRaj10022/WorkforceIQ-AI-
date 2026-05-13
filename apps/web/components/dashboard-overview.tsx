"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type {
  AttritionReportResponse,
  ComplianceListResponse,
  FrontendSessionPayload,
} from "@/types/api";

type DashboardState = {
  session: FrontendSessionPayload | null;
  attrition: AttritionReportResponse | null;
  compliance: ComplianceListResponse | null;
  error: string | null;
  loading: boolean;
};

export function DashboardOverview() {
  const [state, setState] = useState<DashboardState>({
    session: null,
    attrition: null,
    compliance: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let active = true;
    Promise.all([
      requestJson<FrontendSessionPayload>("/api/session"),
      requestJson<AttritionReportResponse>(
        "/api/backend/reports/attrition-risk?limit=5",
      ),
      requestJson<ComplianceListResponse>(
        "/api/backend/compliance/requests?limit=5",
      ),
    ])
      .then(([session, attrition, compliance]) => {
        if (!active) {
          return;
        }
        setState({
          session,
          attrition,
          compliance,
          error: null,
          loading: false,
        });
      })
      .catch((cause) => {
        if (!active) {
          return;
        }
        setState((current) => ({
          ...current,
          error: cause instanceof Error ? cause.message : "Unable to load dashboard.",
          loading: false,
        }));
      });

    return () => {
      active = false;
    };
  }, []);

  if (state.loading) {
    return (
      <div className="grid gap-4">
        <div className="panel rounded-[1.5rem] p-5 text-sm text-muted">
          Loading WorkforceIQ operational summary...
        </div>
      </div>
    );
  }

  if (state.error || !state.attrition || !state.compliance || !state.session) {
    return (
      <div className="rounded-[1.5rem] border border-danger/20 bg-danger/8 px-4 py-4 text-sm text-danger">
        {state.error ?? "Dashboard data is unavailable."}
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Signed-In Role</p>
          <p className="metric mt-4 text-3xl font-semibold">
            {state.session.user?.role ?? "Unknown"}
          </p>
          <p className="mt-2 text-sm text-muted">{state.session.user?.email}</p>
        </article>

        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">High-Risk Employees</p>
          <p className="metric mt-4 text-3xl font-semibold">
            {state.attrition.high_risk_employees.length}
          </p>
          <p className="mt-2 text-sm text-muted">
            Based on the latest attrition model run.
          </p>
        </article>

        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Estimated Exposure</p>
          <p className="metric mt-4 text-3xl font-semibold">
            {formatCurrency(state.attrition.financial_exposure.total_estimated_cost)}
          </p>
          <p className="mt-2 text-sm text-muted">
            1.5x annual salary midpoint for high-risk roles.
          </p>
        </article>

        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Compliance Queue</p>
          <p className="metric mt-4 text-3xl font-semibold">
            {state.compliance.requests.length}
          </p>
          <p className="mt-2 text-sm text-muted">
            Most recent requests available through the API.
          </p>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Executive Summary</p>
          <div className="mt-4 grid gap-3">
            {state.attrition.executive_summary.map((line) => (
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
          <p className="eyebrow">Recent Compliance Activity</p>
          <div className="mt-4 space-y-3">
            {state.compliance.requests.length ? (
              state.compliance.requests.map((request) => (
                <div
                  key={request.id}
                  className="rounded-2xl border border-border bg-white/68 px-4 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold">{request.request_type}</p>
                    <span className="badge badge-neutral">{request.status}</span>
                  </div>
                  <p className="mt-2 text-sm text-muted">
                    Employee {request.subject_employee_id} · {formatDateTime(request.created_at)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No compliance requests yet.</p>
            )}
          </div>
        </article>
      </section>

      <section className="panel rounded-[1.5rem] p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow">High-Risk Employees</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
              Priority retention watchlist
            </h2>
          </div>
          <p className="text-sm text-muted">
            Generated {formatDateTime(state.attrition.generated_at)}
          </p>
        </div>
        <div className="table-shell mt-5">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Department</th>
                <th>Probability</th>
                <th>Confidence</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {state.attrition.high_risk_employees.map((employee) => (
                <tr key={employee.employee_id}>
                  <td>
                    <div className="font-semibold">{employee.employee_name}</div>
                    <div className="mono text-xs text-muted">{employee.employee_id}</div>
                  </td>
                  <td>{employee.department}</td>
                  <td>{Math.round(employee.predicted_attrition_probability * 100)}%</td>
                  <td>{Math.round(employee.confidence * 100)}%</td>
                  <td className="max-w-sm text-sm text-muted">
                    {employee.recommended_action}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
