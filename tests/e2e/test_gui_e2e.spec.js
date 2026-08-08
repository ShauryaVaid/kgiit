// @ts-check
/**
 * tests/e2e/test_gui_e2e.spec.js
 *
 * Playwright browser-level E2E tests for the kgiit GUI.
 *
 * These tests load the GUI's index.html served through a static-files route
 * or navigate directly to the API endpoints and validate the DOM rendering,
 * user interactions, and end-to-end flows.
 *
 * Covers:
 *   - FastAPI docs page loads (Swagger UI)
 *   - Track data renders in API response
 *   - Full learning session flow via browser fetch calls
 *   - Git log viewer error handling via browser
 */
const { test, expect } = require('@playwright/test');

test.describe('GUI: FastAPI Docs Accessibility', () => {
  test('OpenAPI docs page loads successfully', async ({ page }) => {
    // FastAPI auto-generates /docs (Swagger UI)
    await page.goto('/docs');
    await expect(page).toHaveTitle(/kgiit|Swagger|FastAPI/i);

    // Swagger UI should render the API title
    const heading = page.locator('.title');
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test('API redoc page loads successfully', async ({ page }) => {
    await page.goto('/redoc');
    // ReDoc page should contain the API documentation
    await expect(page.locator('body')).toContainText('kgiit', { timeout: 10_000 });
  });
});

test.describe('GUI: Track Listing via Browser', () => {
  test('fetching tracks from browser returns valid JSON', async ({ page }) => {
    // Navigate to a blank page then use fetch to hit the API
    await page.goto('/docs');

    const tracks = await page.evaluate(async () => {
      const res = await fetch('/api/tracks');
      return res.json();
    });

    expect(Array.isArray(tracks)).toBeTruthy();
    expect(tracks.length).toBeGreaterThanOrEqual(1);
    expect(tracks[0]).toHaveProperty('id');
    expect(tracks[0]).toHaveProperty('title');
    expect(tracks[0]).toHaveProperty('lessons_count');
  });
});

test.describe('GUI: Full Learning Session Flow', () => {
  test('complete session lifecycle via browser fetch', async ({ page }) => {
    await page.goto('/docs');

    const result = await page.evaluate(async () => {
      // Step 1: Get available tracks
      const tracksRes = await fetch('/api/tracks');
      const tracks = await tracksRes.json();
      const trackId = tracks[0].id;

      // Step 2: Start a session
      const startRes = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: trackId }),
      });
      const session = await startRes.json();

      // Step 3: Execute a git command
      const execRes = await fetch(`/api/session/${session.session_id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'git status' }),
      });
      const execResult = await execRes.json();

      // Step 4: Check sandbox status
      const statusRes = await fetch(`/api/session/${session.session_id}/status`);
      const status = await statusRes.json();

      // Step 5: Verify lesson
      const verifyRes = await fetch(`/api/session/${session.session_id}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track_id: trackId,
          lesson_index: 0,
          last_command: 'git status',
          exit_code: 0,
          stdout: execResult.stdout,
          stderr: execResult.stderr,
        }),
      });
      const verification = await verifyRes.json();

      // Step 6: Stop session
      const stopRes = await fetch(`/api/session/${session.session_id}/stop`, {
        method: 'POST',
      });
      const stopResult = await stopRes.json();

      return {
        trackId,
        session: {
          id: session.session_id,
          trackTitle: session.track_title,
          lessonTitle: session.lesson_title,
          totalLessons: session.total_lessons,
        },
        execResult: {
          command: execResult.command,
          exitCode: execResult.exit_code,
          hasStdout: execResult.stdout.length > 0 || execResult.stderr.length > 0,
        },
        status: {
          isRepo: status.is_repo,
        },
        verification: {
          hasPassed: typeof verification.passed === 'boolean',
          hasMessage: typeof verification.message === 'string',
        },
        stopped: stopResult.status === 'ok',
      };
    });

    // Validate the entire flow
    expect(result.trackId).toBeTruthy();
    expect(result.session.id).toBeTruthy();
    expect(result.session.trackTitle).toBeTruthy();
    expect(result.session.lessonTitle).toBeTruthy();
    expect(result.session.totalLessons).toBeGreaterThanOrEqual(1);
    expect(result.execResult.command).toBe('git status');
    expect(typeof result.status.isRepo).toBe('boolean');
    expect(result.verification.hasPassed).toBe(true);
    expect(result.verification.hasMessage).toBe(true);
    expect(result.stopped).toBe(true);
  });
});

test.describe('GUI: Lesson Setup and Progression', () => {
  test('lesson setup endpoint resets sandbox for next lesson', async ({ page }) => {
    await page.goto('/docs');

    const result = await page.evaluate(async () => {
      // Get tracks
      const tracksRes = await fetch('/api/tracks');
      const tracks = await tracksRes.json();
      const trackId = tracks[0].id;

      // Start session
      const startRes = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: trackId }),
      });
      const session = await startRes.json();

      // Setup lesson 0 (reset)
      const setupRes = await fetch(
        `/api/session/${session.session_id}/lesson/0/setup`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ track_id: trackId }),
        }
      );
      const setup = await setupRes.json();

      // Cleanup
      await fetch(`/api/session/${session.session_id}/stop`, { method: 'POST' });

      return {
        setupOk: setupRes.ok,
        hasTitle: typeof setup.lesson_title === 'string',
        hasPrompt: typeof setup.lesson_prompt === 'string',
        index: setup.current_index,
      };
    });

    expect(result.setupOk).toBe(true);
    expect(result.hasTitle).toBe(true);
    expect(result.hasPrompt).toBe(true);
    expect(result.index).toBe(0);
  });
});

test.describe('GUI: Error States in Browser', () => {
  test('invalid session shows 404 via browser fetch', async ({ request }) => {
    const response = await request.get('/api/session/nonexistent-session/status');
    expect(response.status()).toBe(404);
  });

  test('invalid track shows 404 on session start', async ({ page }) => {
    await page.goto('/docs');

    const status = await page.evaluate(async () => {
      const res = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: 'fake_track_xyz' }),
      });
      return res.status;
    });

    expect(status).toBe(404);
  });

  test('git log with invalid repo path returns 400', async ({ page }) => {
    await page.goto('/docs');

    const result = await page.evaluate(async () => {
      const res = await fetch('/api/git/log?repo_path=/tmp/nonexistent');
      return { status: res.status, body: await res.json() };
    });

    expect(result.status).toBe(400);
    expect(result.body.detail).toContain('missing .git');
  });
});

test.describe('GUI: ML Hint Integration', () => {
  test('verify endpoint returns ML hints for wrong commands', async ({ page }) => {
    await page.goto('/docs');

    const result = await page.evaluate(async () => {
      // Get tracks & start session
      const tracksRes = await fetch('/api/tracks');
      const tracks = await tracksRes.json();
      const trackId = tracks[0].id;

      const startRes = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: trackId }),
      });
      const session = await startRes.json();

      // Submit a wrong git command to trigger ML hint
      const verifyRes = await fetch(`/api/session/${session.session_id}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track_id: trackId,
          lesson_index: 0,
          last_command: 'git inti',
          exit_code: 1,
          stdout: '',
          stderr: 'git: \'inti\' is not a git command.',
        }),
      });
      const verification = await verifyRes.json();

      // Cleanup
      await fetch(`/api/session/${session.session_id}/stop`, { method: 'POST' });

      return {
        passed: verification.passed,
        hasHint: verification.hint !== null && verification.hint !== undefined,
        hintType: typeof verification.hint,
      };
    });

    expect(result.passed).toBe(false);
    // ML hint should be provided for wrong git commands
    expect(result.hasHint).toBe(true);
    expect(result.hintType).toBe('string');
  });
});
