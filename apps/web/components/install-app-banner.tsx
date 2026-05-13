"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
};

export function InstallAppBanner() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [dismissed, setDismissed] = useState(false);
  const [eligibleOrigin, setEligibleOrigin] = useState(false);

  useEffect(() => {
    const isLoopback =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    const isEligible = window.isSecureContext && !isLoopback;

    setEligibleOrigin(isEligible);

    if (window.localStorage.getItem("wf_install_banner_dismissed") === "1") {
      setDismissed(true);
    }

    if (!isEligible) {
      return;
    }

    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
    };
  }, []);

  if (!eligibleOrigin || !promptEvent || dismissed) {
    return null;
  }

  async function install() {
    const pendingPrompt = promptEvent;
    if (!pendingPrompt) {
      return;
    }

    await pendingPrompt.prompt();
    const choice = await pendingPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setPromptEvent(null);
    }
  }

  return (
    <div className="rounded-[1.5rem] border border-border bg-white/78 px-4 py-4 shadow-[0_18px_80px_rgba(15,23,42,0.12)] backdrop-blur">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="eyebrow">Installable Client</p>
          <p className="mt-2 text-sm leading-6 text-muted">
            Install WorkforceIQ on desktop or mobile for a more app-like
            workspace while keeping the same secured AWS backend.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="button-primary" onClick={install}>
            Install App
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              window.localStorage.setItem("wf_install_banner_dismissed", "1");
              setDismissed(true);
            }}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
