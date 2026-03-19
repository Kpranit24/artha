# File Template — Copy This When Creating Any New File

Every new file in this project must start with this header.
Fill in the sections that apply. Delete sections that don't.

---

## Python file template

```python
# =============================================================
# [path/to/file.py]
# PURPOSE:  [One sentence — what does this file do?]
#
# WHAT IT DOES:
#   [2-3 bullet points explaining the key responsibilities]
#
# DEPENDENCIES:
#   - [What other files/services does this need?]
#   - [What env vars does it read?]
#
# FREE TIER LIMITS:
#   [If this file calls external APIs, list limits here]
#   Example: CoinGecko: 30 req/min → upgrade: $129/mo Pro
#
# UPGRADE PATH:
#   [How would you scale this file up?]
#   [What paid service would replace the free one?]
#
# AI AGENT MONITORS THIS FILE:
#   [Which monitoring agent watches this?]
#   [What does it alert on?]
#
# LAST UPDATED: [Month Year]
# =============================================================
```

## TypeScript/React file template

```typescript
// =============================================================
// [path/to/file.ts]
// PURPOSE:  [One sentence]
//
// WHAT IT DOES:
//   [Key responsibilities]
//
// PROPS (for components):
//   [List props with types and what they do]
//
// CONNECTS TO (for API files):
//   Backend endpoint: [/api/endpoint]
//   Caches: [how long / where]
//
// UPGRADE PATH:
//   [How would you scale this?]
//
// LAST UPDATED: [Month Year]
// =============================================================
```

---

## Function template

Every function should have a docstring explaining:

```python
async def my_function(arg1: str, arg2: int) -> dict:
    """
    [One sentence: what does this do?]

    Args:
        arg1: [what is it, what format]
        arg2: [what is it, what range]

    Returns:
        [what shape, what fields]

    Raises:
        [what errors can it throw?]

    Cache:    [TTL if applicable]
    Cost:     [API call cost if applicable]
    Rate:     [Rate limits if applicable]

    NOTE TO AI AGENTS:
        [Anything monitoring agents should know]

    UPGRADE PATH:
        [How to make this better with paid services]
    """
```

---

## Inline comment template

Use these patterns for non-obvious code:

```python
# WHY: [explain why, not what — the code shows what]
# CHANGE TO: [what to change this to when scaling]
# UPGRADE: [what paid service replaces this]
# TODO: [future work — include ticket/issue number if possible]
# FIXME: [known bug — describe the issue]
# HACK: [temporary fix — explain why and when to remove]
# NOTE TO AI AGENTS: [anything monitoring agents should know]
```

---

## .env variable template

When adding a new environment variable:

```bash
# PURPOSE:    [what is this used for?]
# GET FROM:   [where do you get this value?]
# FREE TIER:  [what's the free limit?]
# PAID:       [what does the paid upgrade cost?]
# REQUIRED:   [will app crash without this? yes/no]
# DEFAULT:    [what's the default if not set?]
MY_NEW_VARIABLE=default_value
```

---

## Review schedule

Every file header has a "LAST UPDATED" date.
Set a calendar reminder to review files every 3 months:
- Are the free tier limits still accurate?
- Have any APIs changed their pricing?
- Are there better free alternatives now?
- Do the upgrade paths still make sense?
