# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the "Label in our tracker" column to match whatever vocabulary you actually use.

## Notes for this repo

- Category roles are the repo's existing `bug` and `enhancement` labels, which `.github/workflows/auto-label.yml` already applies on open. Triage adds the state label; it does not need to create category labels.
- `wontfix` predates this setup (GitHub's default label, white). The other four were created by the setup run.
- `priority/*`, `platform/*`, `component/*` are auto-label output, not triage state. Ignore them when reading state.
