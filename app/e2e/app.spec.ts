import { test } from '@playwright/test'

// No search, no results yet, so there is no money path to drive.
// This placeholder keeps `pnpm run e2e` green until one exists.
test.skip('launches the app and reaches the ready state', () => {
  // TODO: electron.launch() the built app, wait for the ready state,
  // and assert on the rendered content once there is a real UI to check.
})
