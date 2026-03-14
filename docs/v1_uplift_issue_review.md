# Danfoss Ally v1 uplift issue review

This document tracks how the `pydanfossally` v1 uplift affects currently open issues.

## Resolved by backlog merge or uplift

| Issue | Status | Notes |
| --- | --- | --- |
| #147 | Resolved | `hvac_action` now prefers `output_status` and `valve_opening` before stale `work_state`, and PR `#253` is merged. |
| #193 | Resolved | Temperature writes now mirror `manual_mode_fast` after preset/auto writes, including the behavior from PR `#297`. |
| #199 | Resolved | Climate current temperature prefers `external_sensor_temperature` when `radiator_covered` is enabled. |
| #213 | Resolved | Heating Control Scaling is exposed as a select entity and is no longer disabled by default. |
| #295 | Resolved | Large payload logging is kept at debug-oriented code paths only; no info-level payload dumping remains in the integration runtime. |

## Likely resolved, verify against live API

| Issue | Status | Notes |
| --- | --- | --- |
| #255 | Verify after release | The integration now uses the async `pydanfossally` v1 client and a coordinator-backed refresh model. This should address stale write/sync behavior, but needs live verification. |
| #289 | Verify after release | Setup now fails explicitly on auth/connection problems and device loading goes through the v1 client. This should improve empty-device startup failures, but needs live verification. |

## Partially addressed, keep under review

| Issue | Status | Notes |
| --- | --- | --- |
| #109 | Partially addressed | External sensor entities are now created from `ext_measured_rs` as well as `external_sensor_temperature`, but real-world verification is still needed to confirm device/API behavior. |

## Not covered by this uplift

| Issue | Status | Notes |
| --- | --- | --- |
| #187 | Open | No dedicated Icon flow temperature entity was added in this uplift. |
