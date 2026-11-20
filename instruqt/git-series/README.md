# Git integration track series: solved files

Solved files for the three Instruqt tracks on Infrahub Git integration
(`infrahub-git-read-only`, `infrahub-git-read-write`, `infrahub-git-promotion`
in `opsmill/infrahub-instruqt`).

The tracks build their content from `instruqt/track5/base` with the three files
from `instruqt/track5/ch1` copied over it. The learner changes that content by
pasting blocks from the assignments. Solve and setup scripts copy the step
directories below instead.

Each step directory holds the complete files after that step, at their paths
relative to the lab root. Steps are applied in order.

| Step | Feature | Used by |
|---|---|---|
| `f1-syslog-schema` | 1: `syslog_server` with a default value on LocationSite | track 1 solve; tracks 2 and 3 setup |
| `f1-syslog-config` | 1: `logging host` in the router config query and template | track 1 solve; tracks 2 and 3 setup |
| `f2-device` | 2: `ntp_pool` on DcimDevice (first try) | track 2 solve |
| `f2-site` | 2: `ntp_pool` moved to LocationSite | track 2 solve; track 3 setup |
| `f3-login-banner` | 3: `login_banner` with a default value on DcimDevice | track 3 setup |

Each step's query and template build on the steps before it: `f2-*` on `f1-syslog-config`, `f3-login-banner` on `f2-site`. All steps were
imported and rendered on Infrahub 1.12.1.
