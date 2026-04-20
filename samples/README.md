# Sample payloads

Two versions of a `/users` endpoint response for testing the comparator.

## Files

- **users-v1.json** — baseline
- **users-v2.json** — newer response with realistic changes

## How to try it

1. Launch the app.
2. Set **Format** to `JSON`.
3. Click **Load file** on the left pane → pick `users-v1.json`.
4. Click **Load file** on the right pane → pick `users-v2.json`.
5. Set **Ignore** to: `requestId, timestamp`
6. Give it a **Title** like `/users v1 vs v2`.
7. Click **Compare** (or `Ctrl+Enter`).

## What you should see

Without the ignore-list, `requestId` and `timestamp` would flood the diff with noise. With them masked, only the meaningful differences remain:

| Change | Type |
|---|---|
| `pagination.total`: 42 → 43 | **changed** (yellow) |
| `users[0].role`: admin → owner | **changed** (yellow) |
| `users[1].email`: bob → bob.smith | **changed** (yellow) |
| `users[2].active`: false → true | **changed** (yellow) |
| `lastLoginAt` (all three users) | **added** (green) |

Try it a second time **without** the ignore-list to see how much noise the dynamic fields create — that's the whole point of the feature.

Then click **Export HTML** or **Export PDF** to save the report.
