"""
Client-side secret scanner for team memory (PSR M22174).

Scans content for credentials before upload so secrets never leave the
user's machine. Uses a curated subset of high-confidence rules from
gitleaks (https://github.com/gitleaks/gitleaks, MIT license).
"""

import re
from typing import List, Optional, Tuple

from .types import SecretMatch, SecretScanResult


def _capitalize(s: str) -> str:
    if not s:
        return s
    return s[0].upper() + s[1:]


def _rule_id_to_label(rule_id: str) -> str:
    special_case = {
        "aws": "AWS",
        "gcp": "GCP",
        "api": "API",
        "pat": "PAT",
        "ad": "AD",
        "tf": "TF",
        "oauth": "OAuth",
        "npm": "NPM",
        "pypi": "PyPI",
        "jwt": "JWT",
        "github": "GitHub",
        "gitlab": "GitLab",
        "openai": "OpenAI",
        "digitalocean": "DigitalOcean",
        "huggingface": "HuggingFace",
        "hashicorp": "HashiCorp",
        "sendgrid": "SendGrid",
    }
    return " ".join(
        special_case.get(part, _capitalize(part))
        for part in rule_id.split("-")
    )


ANT_KEY_PFX = ["sk", "ant", "api"]


SECRET_RULES: List[Tuple[str, str, Optional[str]]] = [
    ("aws-access-token", r"\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b", None),
    ("gcp-api-key", r"\b(AIza[\w-]{35})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("azure-ad-client-secret", r"(?:^|[\\'\"\x60\s>=:(,)])([a-zA-Z0-9_~.]{3}\dQ~[a-zA-Z0-9_~.-]{31,34})(?:$|[\\'\"\x60\s<),])", None),
    ("digitalocean-pat", r"\b(dop_v1_[a-f0-9]{64})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("digitalocean-access-token", r"\b(doo_v1_[a-f0-9]{64})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("anthropic-api-key", rf"\b({'.'.join(ANT_KEY_PFX)}-03-[a-zA-Z0-9_\-]{{93}}AA)(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("anthropic-admin-api-key", r"\b(sk-ant-admin01-[a-zA-Z0-9_\-]{93}AA)(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("openai-api-key", r"\b(sk-(?:proj|svcacct|admin)-(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})T3BlbkFJ(?:[A-Za-z0-9_-]{74}|[A-Za-z0-9_-]{58})\b|sk-[a-zA-Z0-9]{{20}}T3BlbkFJ[a-zA-Z0-9]{{20}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("huggingface-access-token", r"\b(hf_[a-zA-Z]{{34}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("github-pat", r"ghp_[0-9a-zA-Z]{36}", None),
    ("github-fine-grained-pat", r"github_pat_\w{82}", None),
    ("github-app-token", r"(?:ghu|ghs)_[0-9a-zA-Z]{36}", None),
    ("github-oauth", r"gho_[0-9a-zA-Z]{36}", None),
    ("github-refresh-token", r"ghr_[0-9a-zA-Z]{36}", None),
    ("gitlab-pat", r"glpat-[\w-]{20}", None),
    ("gitlab-deploy-token", r"gldt-[0-9a-zA-Z_\-]{20}", None),
    ("slack-bot-token", r"xoxb-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*", None),
    ("slack-user-token", r"xox[pe](?:-[0-9]{10,13}){{3}}-[a-zA-Z0-9-]{{28,34}}", None),
    ("slack-app-token", r"xapp-\d-[A-Z0-9]+-\d+-[a-z0-9]+", "i"),
    ("twilio-api-key", r"SK[0-9a-fA-F]{{32}}", None),
    ("sendgrid-api-token", r"\b(SG\.[a-zA-Z0-9=_\-.]{{66}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("npm-access-token", r"\b(npm_[a-zA-Z0-9]{{36}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("pypi-upload-token", r"pypi-AgEIcHlwaS5vcmc[\w-]{{50,1000}}", None),
    ("databricks-api-token", r"\b(dapi[a-f0-9]{{32}}(?:-\d)?)(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("hashicorp-tf-api-token", r"[a-zA-Z0-9]{{14}}\.atlasv1\.[a-zA-Z0-9\-_=]{{60,70}}", None),
    ("pulumi-api-token", r"\b(pul-[a-f0-9]{{40}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("postman-api-token", r"\b(PMAK-[a-fA-F0-9]{{24}}-[a-fA-F0-9]{{34}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("grafana-api-key", r"\b(eyJrIjoi[A-Za-z0-9+/]{{70,400}}={0,3})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("grafana-cloud-api-token", r"\b(glc_[A-Za-z0-9+/]{{32,400}}={0,3})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("grafana-service-account-token", r"\b(glsa_[A-Za-z0-9]{{32}}_[A-Fa-f0-9]{{8}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("sentry-user-token", r"\b(sntryu_[a-f0-9]{{64}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("sentry-org-token", r"\bsntrys_eyJpYXQiO[a-zA-Z0-9+/]{{10,200}}(?:LCJyZWdpb25fdXJs|InJlZ2lvbl91cmwi|cmVnaW9uX3VybCI6)[a-zA-Z0-9+/]{{10,200}}={0,2}_[a-zA-Z0-9+/]{{43}}", None),
    ("stripe-access-token", r"\b((?:sk|rk)_(?:test|live|prod)_[a-zA-Z0-9]{{10,99}})(?:[\x60'\"\s;]|\\[nr]|$)", None),
    ("shopify-access-token", r"shpat_[a-fA-F0-9]{{32}}", None),
    ("shopify-shared-secret", r"shpss_[a-fA-F0-9]{{32}}", None),
    ("private-key", r"-----BEGIN[ A-Z0-9_-]{{0,100}}PRIVATE KEY(?: BLOCK)?-----[\s\S-]{{64,}}?-----END[ A-Z0-9_-]{{0,100}}PRIVATE KEY(?: BLOCK)?-----", "i"),
]


_compiled_rules: Optional[List[Tuple[str, re.Pattern]]] = None


def _get_compiled_rules() -> List[Tuple[str, re.Pattern]]:
    global _compiled_rules
    if _compiled_rules is None:
        _compiled_rules = []
        for rule_id, source, flags in SECRET_RULES:
            pattern = re.compile(source, flags or "")
            _compiled_rules.append((rule_id, pattern))
    return _compiled_rules


def scan_for_secrets(content: str) -> List[SecretMatch]:
    matches: List[SecretMatch] = []
    seen = set()

    for rule_id, pattern in _get_compiled_rules():
        if rule_id in seen:
            continue
        if pattern.search(content):
            seen.add(rule_id)
            matches.append(SecretMatch(
                rule_id=rule_id,
                label=_rule_id_to_label(rule_id),
            ))

    return matches


def is_secret_pattern(content: str) -> bool:
    return len(scan_for_secrets(content)) > 0


def get_secret_label(rule_id: str) -> str:
    return _rule_id_to_label(rule_id)


def redact_secrets(content: str) -> str:
    for _, pattern in _get_compiled_rules():
        def replace_func(match: re.Match) -> str:
            g1 = match.group(1) if match.groups() else None
            if isinstance(g1, str):
                return match.group(0).replace(g1, "[REDACTED]")
            return "[REDACTED]"

        content = pattern.sub(replace_func, content)
    return content


def scan_file(file_path: str, content: str) -> SecretScanResult:
    matches = scan_for_secrets(content)
    return SecretScanResult.from_matches(matches)
