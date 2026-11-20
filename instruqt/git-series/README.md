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
| `f1-router` | 1: router AMS-RTR-02 at ams-01, no management address | track 1 solve; tracks 2 and 3 setup |
| `f1-address` | 1: 172.16.1.5/24 as primary address of AMS-RTR-02 | track 1 solve; tracks 2 and 3 setup |
| `f2-device` | 2: `ntp_pool` on DcimDevice (first try) | track 2 solve |
| `f2-site` | 2: `ntp_pool` moved to LocationSite | track 2 solve; track 3 setup |
| `f3-login-banner` | 3: `login_banner` with a default value on DcimDevice | track 3 setup |

`f3-login-banner` builds on `f2-site` (query and template). All steps were
imported and rendered on Infrahub 1.12.1.
