import Link from "next/link";
import { redirect } from "next/navigation";

import { InstallAppBanner } from "@/components/install-app-banner";
import { getPublicAppConfig } from "@/lib/env";
import { readPortalSession } from "@/lib/session";

type HomePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

async function fetchHealth(apiBaseUrl: string) {
  try {
    const response = await fetch(`${apiBaseUrl}/api/health`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return { status: "degraded", detail: `HTTP ${response.status}` };
    }
    const payload = (await response.json()) as {
      environment?: string;
      status?: string;
      version?: string;
    };
    return {
      status: payload.status ?? "unknown",
      detail: `${payload.environment ?? "unknown"} · v${payload.version ?? "?"}`,
    };
  } catch {
    return {
      status: "pending",
      detail: "Backend deploy pending or unreachable from this frontend.",
    };
  }
}

function decodeErrorMessage(value: string) {
  let decoded = value.trim();

  for (let attempts = 0; attempts < 2; attempts += 1) {
    try {
      const next = decodeURIComponent(decoded);
      if (next === decoded) {
        break;
      }
      decoded = next;
    } catch {
      break;
    }
  }

  return decoded;
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const session = await readPortalSession();
  if (session) {
    redirect("/portal");
  }

  const config = getPublicAppConfig();
  const params = await searchParams;
  const errorParam = params.error;
  const noticeParam = params.notice;
  const error =
    typeof errorParam === "string" && errorParam.trim()
      ? decodeErrorMessage(errorParam)
      : null;
  const notice =
    typeof noticeParam === "string" && noticeParam.trim()
      ? decodeErrorMessage(noticeParam)
      : null;
  const errorHint = error?.includes("Email domain")
    ? "Use an approved work email domain or ask an administrator to expand the signup allowlist."
    : error?.includes("Sign-in verification failed")
      ? "If you started sign-in from an old localhost install, remove it and reinstall from the live site."
      : null;
  const transportWarning =
    config.apiBaseUrl.startsWith("http://") &&
    !config.apiBaseUrl.startsWith("http://localhost") &&
    !config.apiBaseUrl.startsWith("http://127.0.0.1");
  const health = await fetchHealth(config.apiBaseUrl);

  return (
    <main className="shell-grid min-h-screen px-5 py-6 sm:px-8 lg:px-10">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-7xl flex-col gap-6">
        <InstallAppBanner />

        <section className="panel-strong relative overflow-hidden rounded-[2rem] px-6 py-8 sm:px-10 sm:py-10 lg:px-12">
          <div className="hero-orbit" />
          <div className="grid gap-10 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="space-y-8">
              <div className="space-y-4">
                <p className="eyebrow">WorkforceIQ Portal</p>
                <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.06em] text-balance sm:text-5xl lg:text-6xl">
                  Workforce operations, reporting, identity, and governed
                  employee access in one cloud-ready control surface.
                </h1>
                <p className="max-w-3xl text-base leading-7 text-muted sm:text-lg">
                  This frontend is built directly against the WorkforceIQ
                  backend contract: Cognito hosted sign-in, WorkforceIQ token
                  exchange, employee search, department health, attrition
                  reporting, audit review, and compliance workflows.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link href="/auth/login" className="button-primary">
                  Sign In With Cognito
                </Link>
                <a
                  className="button-secondary"
                  href="https://docs.aws.amazon.com/cognito/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Cognito Architecture
                </a>
              </div>

              {notice ? (
                <div className="rounded-2xl border border-border bg-white/72 px-4 py-3 text-sm text-foreground shadow-[0_12px_40px_rgba(15,23,42,0.08)]">
                  {notice}
                </div>
              ) : null}

              {error ? (
                <div className="rounded-2xl border border-danger/20 bg-danger/8 px-4 py-3 text-sm text-danger">
                  <p>{error}</p>
                  {errorHint ? (
                    <p className="mt-2 text-danger/80">{errorHint}</p>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
              <div className="panel rounded-[1.5rem] p-5">
                <div className="flex items-center justify-between">
                  <p className="eyebrow">Backend Link</p>
                  <span
                    className={`badge ${
                      health.status === "ok"
                        ? "badge-success"
                        : health.status === "pending"
                          ? "badge-warning"
                          : "badge-danger"
                    }`}
                  >
                    <span
                      className={`status-dot ${
                        health.status === "ok"
                          ? "ok"
                          : health.status === "pending"
                            ? "warn"
                            : "fail"
                      }`}
                    />
                    {health.status}
                  </span>
                </div>
                <p className="mt-4 text-3xl font-semibold tracking-[-0.06em]">
                  WorkforceIQ API
                </p>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {health.detail}
                </p>
                {transportWarning ? (
                  <p className="mt-3 rounded-2xl border border-warning/25 bg-warning/10 px-3 py-2 text-xs leading-5 text-warning">
                    Frontend auth is live, but the backend API is still exposed
                    over HTTP. Attach ACM and move the API to HTTPS before
                    production launch.
                  </p>
                ) : null}
              </div>

              <div className="panel rounded-[1.5rem] p-5">
                <p className="eyebrow">Integrated Capabilities</p>
                <div className="mt-4 grid gap-3 text-sm text-muted">
                  <p>Employee search and profile update workflow</p>
                  <p>Department health and attrition reporting</p>
                  <p>Audit and compliance request visibility</p>
                  <p>Session-bound auth with Cognito plus WorkforceIQ RBAC</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Identity</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Cognito plus WorkforceIQ session control
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Users authenticate through Cognito, then the frontend exchanges
              the Cognito ID token for WorkforceIQ access and refresh tokens so
              RBAC, audit, and logout revocation stay inside the product.
            </p>
          </article>

          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Operations</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Built for workforce operations, not just profile browsing
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              The portal surfaces the backend’s existing domain: workforce
              search, employee update controls, risk reporting, department
              health, audit evidence, and compliance requests.
            </p>
          </article>

          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Cloud Path</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Structured for AWS rollout
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Terraform provisions Cognito, ECR, EC2, ALB, RDS, Redis, S3, and
              Secrets Manager. The frontend consumes the exact env surface
              emitted by `terraform output frontend_env`.
            </p>
          </article>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Mobile-Operable</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Installable on phones and desktops
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              The portal is now structured as an installable client surface,
              which lets you run the same secured WorkforceIQ experience on
              laptop browsers, mobile browsers, and later native desktop/mobile
              shells.
            </p>
          </article>

          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Encryption</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Encrypted infrastructure, token isolation, and tighter headers
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Session tokens remain in HTTP-only cookies, Cognito drives the
              identity layer, and the AWS stack now carries encrypted RDS,
              encrypted Redis transit, Secrets Manager, and stricter frontend
              browser policies.
            </p>
          </article>

          <article className="panel rounded-[1.5rem] p-6">
            <p className="eyebrow">Open Source Path</p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.05em]">
              Ready to wrap in a native open-source shell
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              The next packaging layer is a Tauri 2 shell so the same client can
              be published as an open-source Windows desktop app and later as
              Android and iOS builds with a shared codebase.
            </p>
          </article>
        </section>
      </div>
    </main>
  );
}
