"use client";

import { useEffect, useState } from "react";

import { requestJson } from "@/lib/client-api";
import { formatDateTime, formatPercent } from "@/lib/format";
import type {
  EmployeeProfileResponse,
  EmployeeUpdateResponse,
  PredictionPayload,
} from "@/types/api";

type EmployeeProfileProps = {
  employeeId: string;
};

function PredictionCard({
  label,
  prediction,
}: {
  label: string;
  prediction: PredictionPayload | null;
}) {
  if (!prediction) {
    return (
      <div className="rounded-2xl border border-border bg-white/68 px-4 py-4 text-sm text-muted">
        {label}: not available.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-white/68 px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold">{label}</p>
        <span
          className={`badge ${
            prediction.stale ? "badge-warning" : "badge-success"
          }`}
        >
          {prediction.stale ? "Stale" : "Current"}
        </span>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-[-0.05em]">
        {formatPercent(prediction.prediction)}
      </p>
      <p className="mt-2 text-sm text-muted">
        Confidence {formatPercent(prediction.confidence)} ·{" "}
        {formatDateTime(prediction.run_at)}
      </p>
      <p className="mt-3 text-sm leading-6 text-muted">
        {prediction.recommended_action}
      </p>
    </div>
  );
}

export function EmployeeProfile({ employeeId }: EmployeeProfileProps) {
  const [payload, setPayload] = useState<EmployeeProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftEmail, setDraftEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    requestJson<EmployeeProfileResponse>(`/api/backend/employees/${employeeId}`)
      .then((response) => {
        if (!active) {
          return;
        }
        setPayload(response);
        setDraftName(response.employee_profile.name);
        setDraftEmail(response.employee_profile.email);
        setError(null);
      })
      .catch((cause) => {
        if (!active) {
          return;
        }
        setError(
          cause instanceof Error ? cause.message : "Unable to load employee profile.",
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
  }, [employeeId]);

  async function saveProfile() {
    setSaving(true);
    setNotice(null);
    setError(null);

    try {
      const response = await requestJson<EmployeeUpdateResponse>(
        `/api/backend/employees/${employeeId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            name: draftName,
            email: draftEmail,
          }),
        },
      );
      setNotice(`${response.message} Changed: ${response.changed_fields.join(", ")}`);
      const refreshed = await requestJson<EmployeeProfileResponse>(
        `/api/backend/employees/${employeeId}`,
      );
      setPayload(refreshed);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to update employee.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="panel rounded-[1.5rem] p-5 text-sm text-muted">
        Loading employee profile...
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="rounded-[1.5rem] border border-danger/20 bg-danger/8 px-4 py-4 text-sm text-danger">
        {error ?? "Employee profile is unavailable."}
      </div>
    );
  }

  const profile = payload.employee_profile;
  const predictions = payload.ml_predictions;

  return (
    <div className="grid gap-5">
      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Employee Record</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <p className="eyebrow">Name</p>
              <p className="mt-2 text-2xl font-semibold tracking-[-0.05em]">
                {profile.name}
              </p>
            </div>
            <div>
              <p className="eyebrow">Employee ID</p>
              <p className="mono mt-2 text-xl font-semibold">{profile.id}</p>
            </div>
            <div>
              <p className="eyebrow">Role</p>
              <p className="mt-2 text-sm">{profile.role.title}</p>
              <p className="text-sm text-muted">{profile.role.level}</p>
            </div>
            <div>
              <p className="eyebrow">Department</p>
              <p className="mt-2 text-sm">{profile.department.name}</p>
              <p className="text-sm text-muted">ID {profile.department.id}</p>
            </div>
            <div>
              <p className="eyebrow">Status</p>
              <p className="mt-2 text-sm">{profile.status.value}</p>
            </div>
            <div>
              <p className="eyebrow">Manager</p>
              <p className="mt-2 text-sm">{profile.manager.name ?? "Unassigned"}</p>
            </div>
            <div>
              <p className="eyebrow">Hire Date</p>
              <p className="mt-2 text-sm">{profile.tenure.hire_date}</p>
            </div>
            <div>
              <p className="eyebrow">Tenure</p>
              <p className="mt-2 text-sm">{profile.tenure.years} years</p>
            </div>
          </div>
          <div className="mt-5 rounded-2xl border border-border bg-white/68 px-4 py-4">
            <p className="eyebrow">Formatted Summary</p>
            <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted">
              {payload.formatted_summary}
            </pre>
          </div>
        </article>

        <article className="panel rounded-[1.5rem] p-5">
          <p className="eyebrow">Update Record</p>
          <div className="mt-4 grid gap-3">
            <input
              className="field"
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              placeholder="Employee name"
            />
            <input
              className="field"
              value={draftEmail}
              onChange={(event) => setDraftEmail(event.target.value)}
              placeholder="Employee email"
            />
            <button
              type="button"
              className="button-primary"
              onClick={saveProfile}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save WorkforceIQ Update"}
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

          <div className="mt-5 rounded-2xl border border-border bg-white/68 px-4 py-4">
            <p className="eyebrow">Join Logic</p>
            <ul className="mt-3 grid gap-2 text-sm text-muted">
              {payload.join_logic.map((entry) => (
                <li key={entry} className="mono">
                  {entry}
                </li>
              ))}
            </ul>
          </div>
        </article>
      </section>

      <section className="panel rounded-[1.5rem] p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow">ML Signals</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
              Risk and readiness signals
            </h2>
          </div>
        </div>

        {"restricted" in predictions ? (
          <div className="mt-5 rounded-2xl border border-warning/20 bg-warning/8 px-4 py-4 text-sm text-warning">
            {predictions.reason}
          </div>
        ) : (
          <div className="mt-5 grid gap-4 xl:grid-cols-3">
            <PredictionCard
              label="Attrition Risk"
              prediction={predictions.attrition_risk}
            />
            <PredictionCard
              label="Performance Forecast"
              prediction={predictions.performance_forecast}
            />
            <PredictionCard
              label="Promotion Readiness"
              prediction={predictions.promotion_readiness}
            />
          </div>
        )}
      </section>
    </div>
  );
}
