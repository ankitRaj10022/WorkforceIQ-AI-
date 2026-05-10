from __future__ import annotations

from workforceiq.ai import build_runtime_system_prompt
from workforceiq.ai.system_prompt import load_master_system_prompt


def test_master_prompt_loads_from_repo():
    prompt = load_master_system_prompt()

    assert "WorkforceIQ AI" in prompt
    assert "Role-aware responses" in prompt


def test_runtime_prompt_includes_active_context():
    prompt = build_runtime_system_prompt(role="HR_MANAGER", scope="Global")

    assert "Active role: HR_MANAGER" in prompt
    assert "Active scope: Global" in prompt
