# Rule template

> Copy this file to `{{RULES_DIR}}/templates/TEMPLATE-RULE-v1.md` and resolve every `{{PLACEHOLDER}}` (INV-8, INV-20 — never at the rules root directly). See [`INSTANTIATION-GUIDE.md`](../INSTANTIATION-GUIDE.md).

Use this template to create one concrete rule file per rule under the relevant
rule-type directory, for example `{{RULES_DIR}}/{{RULE_TYPE_DIR}}/{{RULE_SLUG}}.md`.

## Rule metadata

- **Type**: `{{RULE_TYPE}}`
- **Domain**: `{{DOMAIN_CODE}}`
- **Status**: ✅ working
- **Strength**: `{{RULE_STRENGTH}}` — `must`, `should` or `may`; `must` when left out (`FORMAT.md` §5.2)
- **Targets**: `{{TARGET_RULE_IDS}}`

## Rule

{{RULE_TEXT}}

## Notes

- Source: `{{SOURCE_REFERENCE}}`
- Related rules: `{{RELATED_RULE_IDS}}`
