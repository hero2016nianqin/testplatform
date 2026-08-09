# API Reference

Base URL: `/api/v1`

## Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Login |
| POST | `/auth/logout` | None | Logout |
| GET | `/auth/me` | None | Current user |
| GET | `/auth/users` | developer+ | List users |
| POST | `/auth/users` | developer+ | Create user |
| PUT | `/auth/users/{id}` | developer+ | Update user |
| DELETE | `/auth/users/{id}` | super_admin | Delete user |

## Stations

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/stations/factories` | None | List factories |
| POST | `/stations/factories` | developer | Create factory |
| PUT | `/stations/factories/{id}` | developer | Update factory |
| DELETE | `/stations/factories/{id}` | developer | Delete factory |
| GET | `/stations/lines` | None | List lines |
| POST | `/stations/lines` | developer | Create line |
| PUT | `/stations/lines/{id}` | developer | Update line |
| DELETE | `/stations/lines/{id}` | developer | Delete line |
| GET | `/stations/definitions` | None | List definitions |
| POST | `/stations/definitions` | developer | Create definition |
| PUT | `/stations/definitions/{id}` | developer | Update definition |
| GET | `/stations` | None | List stations |
| POST | `/stations` | developer | Create station |
| GET | `/stations/{id}` | None | Station detail (hierarchy) |
| PUT | `/stations/{id}` | process | Update station |
| DELETE | `/stations/{id}` | developer | Delete station |
| GET | `/stations/{id}/equipment` | None | Get equipment config |
| PUT | `/stations/{id}/equipment` | process | Update equipment config |
| GET | `/stations/{id}/hardware` | None | List hardware params |
| POST | `/stations/{id}/hardware` | process | Create hardware param |
| PUT | `/stations/hardware/{id}` | process | Update hardware param |
| DELETE | `/stations/hardware/{id}` | process | Delete hardware param |
| PUT | `/stations/{id}/hardware/batch` | developer | Batch replace hardware |
| GET | `/stations/{id}/software` | None | Get software config |
| PUT | `/stations/{id}/software` | developer | Update software config |
| GET | `/stations/{id}/scenario` | None | Get scenario config |
| PUT | `/stations/{id}/scenario` | process | Update scenario config |
| GET | `/stations/{id}/metrics` | None | Get metrics |
| PUT | `/stations/{id}/metrics` | developer | Update metrics |
| GET | `/stations/{id}/property-page` | None | Get property page |
| PUT | `/stations/{id}/property-page` | process | Update property page |
| GET | `/stations/{id}/version-check` | None | Check version |
| POST | `/stations/{id}/update-version` | developer | Update deployed version |
| GET | `/stations/{id}/deployed-version` | None | Get deployed version |

## Tests

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/tests/items` | None | List test items |
| POST | `/tests/items` | developer | Create test item |
| PUT | `/tests/items/{id}` | developer | Update test item |
| DELETE | `/tests/items/{id}` | developer | Delete test item |
| GET | `/tests/templates` | None | List templates |
| POST | `/tests/templates` | developer | Create template |
| PUT | `/tests/templates/{id}` | developer | Update template |
| DELETE | `/tests/templates/{id}` | developer | Delete template |
| GET | `/tests/sequences` | None | List sequences |
| GET | `/tests/sequences/{id}` | None | Get sequence detail |
| POST | `/tests/sequences` | developer | Create sequence |
| PUT | `/tests/sequences/{id}` | developer | Update sequence |
| DELETE | `/tests/sequences/{id}` | developer | Delete sequence |
| GET | `/tests/runs` | None | List runs |
| POST | `/tests/runs` | None | Create run |
| PUT | `/tests/runs/{id}` | None | Update run |
| POST | `/tests/runs/{id}/results` | None | Submit result |
| POST | `/tests/scan` | None | Scan-to-test |
| GET | `/tests/records` | None | Query records (R1/R2/R3) |

## Versions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/versions` | current_user | List versions |
| POST | `/versions` | developer | Create version |
| GET | `/versions/{id}` | None | Get version |
| PUT | `/versions/{id}` | developer | Update version (draft) |
| DELETE | `/versions/{id}` | super_admin | Delete version |
| POST | `/versions/{id}/delist` | super_admin | Delist version |
| POST | `/versions/{id}/restore` | super_admin | Restore version |
| GET | `/versions/{id}/sub-scenarios` | None | List sub-scenarios |
| POST | `/versions/{id}/sub-scenarios` | developer | Create sub-scenario |
| PUT | `/versions/sub-scenarios/{id}` | developer | Update sub-scenario |
| DELETE | `/versions/sub-scenarios/{id}` | developer | Delete sub-scenario |
| POST | `/versions/{id}/assign-approvers` | developer | Set approval steps |
| POST | `/versions/{id}/submit-step` | current_user | Submit approval |
| GET | `/versions/{id}/binaries` | None | List binary files |
| POST | `/versions/{id}/binaries` | developer | Upload binary |
| DELETE | `/versions/{id}/binaries/{fid}` | developer | Delete binary |
| GET | `/versions/{id}/binaries/{fid}/download` | None | Download binary |
| POST | `/versions/{id}/deployments` | developer | Create deployment |
| POST | `/versions/deployments/{id}/approve` | current_user | Approve deployment |
| POST | `/versions/deployments/{id}/execute` | developer | Execute deployment |
| GET | `/versions/pending-approvals` | current_user | Pending approvals |
| GET | `/versions/next-version` | current_user | Suggest next version |
| GET | `/versions/all-users` | current_user | List users |
| GET | `/versions/archive-configs` | current_user | List archive configs |

## Logs

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/logs` | None | List logs |
| GET | `/logs/stats` | None | Log statistics |
| GET | `/logs/export` | None | Export CSV |

## Init

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/init` | developer | Initialize system |
| POST | `/init/reset` | super_admin | Reset system |

## WebSocket

| Type | Path | Description |
|---|---|---|
| WS | `/ws/stations/{id}` | Station channel |
| WS | `/ws/global` | Global channel |

Events: `run_started`, `item_tested`, `run_completed`, `run_failed`, `ping`/`pong`

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
