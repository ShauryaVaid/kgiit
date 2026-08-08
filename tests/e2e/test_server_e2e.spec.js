// @ts-check
/**
 * tests/e2e/test_server_e2e.spec.js
 *
 * Playwright E2E tests for the kgiit FastAPI server API endpoints.
 * Uses Playwright's built-in APIRequestContext for HTTP-level E2E testing.
 *
 * Covers:
 *   - Track listing
 *   - Session lifecycle (start → execute → status → verify → stop)
 *   - Git log endpoint
 *   - Error handling for invalid inputs
 */
const { test, expect } = require('@playwright/test');

test.describe('API: Track Listing', () => {
  test('GET /api/tracks returns a list of available tracks', async ({ request }) => {
    const response = await request.get('/api/tracks');
    expect(response.ok()).toBeTruthy();

    const tracks = await response.json();
    expect(Array.isArray(tracks)).toBeTruthy();
    expect(tracks.length).toBeGreaterThanOrEqual(1);

    // Each track must have required fields
    for (const track of tracks) {
      expect(track).toHaveProperty('id');
      expect(track).toHaveProperty('title');
      expect(track).toHaveProperty('description');
      expect(track).toHaveProperty('lessons_count');
      expect(typeof track.id).toBe('string');
      expect(typeof track.title).toBe('string');
      expect(track.lessons_count).toBeGreaterThanOrEqual(1);
    }
  });
});

test.describe('API: Session Lifecycle', () => {
  let sessionId;
  let trackId;

  test.beforeAll(async ({ request }) => {
    // Discover the first available track
    const tracksRes = await request.get('/api/tracks');
    const tracks = await tracksRes.json();
    trackId = tracks[0].id;
  });

  test('POST /api/session/start creates a new session', async ({ request }) => {
    const response = await request.post('/api/session/start', {
      data: { track_id: trackId },
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('session_id');
    expect(body).toHaveProperty('track_title');
    expect(body).toHaveProperty('lesson_title');
    expect(body).toHaveProperty('lesson_prompt');
    expect(body).toHaveProperty('total_lessons');
    expect(body).toHaveProperty('current_index');
    expect(body.current_index).toBe(0);
    expect(body.total_lessons).toBeGreaterThanOrEqual(1);

    sessionId = body.session_id;
  });

  test('GET /api/session/{id}/status returns sandbox state', async ({ request }) => {
    const response = await request.get(`/api/session/${sessionId}/status`);
    expect(response.ok()).toBeTruthy();

    const state = await response.json();
    // Sandbox state must include repo status fields
    expect(state).toHaveProperty('is_repo');
    expect(typeof state.is_repo).toBe('boolean');
  });

  test('POST /api/session/{id}/execute runs a git command', async ({ request }) => {
    const response = await request.post(`/api/session/${sessionId}/execute`, {
      data: { command: 'git status' },
    });
    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result).toHaveProperty('command', 'git status');
    expect(result).toHaveProperty('exit_code');
    expect(result).toHaveProperty('stdout');
    expect(result).toHaveProperty('stderr');
    expect(typeof result.exit_code).toBe('number');
  });

  test('POST /api/session/{id}/execute handles invalid commands gracefully', async ({ request }) => {
    const response = await request.post(`/api/session/${sessionId}/execute`, {
      data: { command: 'nonexistent_binary_xyz' },
    });
    expect(response.ok()).toBeTruthy();

    const result = await response.json();
    expect(result.exit_code).not.toBe(0);
    expect(result.stderr.length).toBeGreaterThan(0);
  });

  test('POST /api/session/{id}/verify checks lesson completion', async ({ request }) => {
    const response = await request.post(`/api/session/${sessionId}/verify`, {
      data: {
        track_id: trackId,
        lesson_index: 0,
        last_command: 'git status',
        exit_code: 0,
        stdout: '',
        stderr: '',
      },
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('passed');
    expect(body).toHaveProperty('message');
    expect(typeof body.passed).toBe('boolean');
    expect(typeof body.message).toBe('string');
  });

  test('POST /api/session/{id}/stop terminates the session', async ({ request }) => {
    const response = await request.post(`/api/session/${sessionId}/stop`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('ok');
  });

  test('GET /api/session/{id}/status returns 404 after stop', async ({ request }) => {
    const response = await request.get(`/api/session/${sessionId}/status`);
    expect(response.status()).toBe(404);
  });
});

test.describe('API: Error Handling', () => {
  test('POST /api/session/start with invalid track returns 404', async ({ request }) => {
    const response = await request.post('/api/session/start', {
      data: { track_id: 'nonexistent_track_xyz' },
    });
    expect(response.status()).toBe(404);
  });

  test('GET /api/session/fake-id/status returns 404', async ({ request }) => {
    const response = await request.get('/api/session/fake-id-12345/status');
    expect(response.status()).toBe(404);
  });

  test('POST /api/session/fake-id/execute returns 404', async ({ request }) => {
    const response = await request.post('/api/session/fake-id-12345/execute', {
      data: { command: 'git status' },
    });
    expect(response.status()).toBe(404);
  });
});

test.describe('API: Git Log Endpoint', () => {
  test('GET /api/git/log with invalid path returns 400', async ({ request }) => {
    const response = await request.get('/api/git/log', {
      params: { repo_path: '/tmp/nonexistent_repo_xyz' },
    });
    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.detail).toContain('missing .git');
  });

  test('GET /api/git/log with path traversal returns 400', async ({ request }) => {
    const response = await request.get('/api/git/log', {
      params: { repo_path: '../../../../etc' },
    });
    expect(response.status()).toBe(400);
  });
});
