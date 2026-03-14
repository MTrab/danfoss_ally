# Danfoss Ally v1 uplift breaking changes

## Current assessment

No intentional user-facing breaking changes are required for the current uplift branch.

## Compatibility measures already included

- Existing climate, sensor, binary sensor, switch, and select unique IDs are preserved as far as practical.
- Legacy preset service values `holiday` and `holiday_sat` are still accepted and normalized internally.
- Existing custom climate services are retained.
- Existing credentials-based setup remains supported.

## Items to verify before merge

- Entity display names may differ slightly for new installations because entities now use translation-backed names.
- Re-auth and reconfigure flows are new; they should be noted in release notes as improvements, not breaking changes.
- If any future `pydanfossally` branch pin is needed during development, it must be reverted before merge and release.
