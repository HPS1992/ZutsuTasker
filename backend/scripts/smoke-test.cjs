const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { execFileSync, spawn } = require('node:child_process');

const root = path.resolve(__dirname, '..');
// Set PG_BIN when PostgreSQL tools are not on PATH.
const pg = process.env.PG_BIN || '';
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'zutsu-backend-smoke-'));
const data = path.join(temporary, 'database');
const pgPort = 49152 + Math.floor(Math.random() * 5000);
const apiPort = pgPort + 1;
const env = { ...process.env, DATABASE_URL: `postgresql://zutsu@127.0.0.1:${pgPort}/postgres`, PORT: String(apiPort), NODE_ENV: 'production', JWT_SECRET: 'zutsu-local-smoke-only' };
let server;
let databaseStarted = false;
let serverLog = '';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  try {
    execFileSync(path.join(pg, 'initdb'), ['-D', data, '-U', 'zutsu', '-A', 'trust', '--no-locale'], { stdio: 'pipe' });
    execFileSync(path.join(pg, 'pg_ctl'), ['-D', data, '-l', path.join(temporary, 'postgres.log'), '-o', `-h 127.0.0.1 -p ${pgPort} -k ${temporary}`, '-w', 'start'], { stdio: 'pipe' });
    databaseStarted = true;
    execFileSync(path.join(root, 'node_modules/.bin/prisma'), ['db', 'push', '--skip-generate'], { cwd: root, env, stdio: 'pipe' });
    server = spawn(process.execPath, ['dist/server.js'], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
    server.stdout.on('data', value => { serverLog += value; });
    server.stderr.on('data', value => { serverLog += value; });
    let ready = false;
    for (let i = 0; i < 100; i++) {
      if (server.exitCode !== null) throw new Error(`Server exited: ${serverLog}`);
      try { ready = (await fetch(`http://127.0.0.1:${apiPort}/health`)).ok; } catch {}
      if (ready) break;
      await delay(100);
    }
    assert(ready, 'Production server must listen and return health');
    let token;
    async function api(route, body, method = body === undefined ? 'GET' : 'POST') {
      const response = await fetch(`http://127.0.0.1:${apiPort}/api${route}`, {
        method,
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) })
      });
      const payload = await response.json();
      assert(response.ok, `${method} ${route}: ${response.status} ${JSON.stringify(payload)}`);
      return payload;
    }
    const credentials = { email: 'smoke@zutsu.invalid', password: 'TemporaryTest123!' };
    const registered = await api('/auth/local-register', { ...credentials, name: 'Prueba local' });
    assert(registered.user.id && registered.token);
    const login = await api('/auth/local-login', credentials);
    token = login.token;
    assert.equal(login.user.id, registered.user.id);
    assert.equal((await api('/users/dashboard')).groupId, null);
    const group = await api('/group/create', { name: 'Hogar temporal' });
    assert.equal((await api('/users/dashboard')).groupId, group.id);
    const created = await api('/tasks', { title: 'Tarea temporal', points: '30', frequency: 'ONCE', assignment_type: 'FIXED', fixed_user_id: registered.user.id, start_date: new Date(Date.now() + 86400000).toISOString() });
    const tasks = await api('/tasks');
    assert.equal(tasks.length, 1);
    assert.equal(tasks[0].assigned_to.id, registered.user.id);
    assert.equal((await api(`/tasks/${created.instance.id}/complete`, {})).success, true);
    assert.equal((await api('/users/dashboard')).totalPoints, 30);
    const reward = await api('/rewards', { title: 'Premio temporal', cost_points: 10, icon_name: 'pizza', image_uri: 'test-image' });
    assert.equal(reward.icon_name, 'pizza');
    assert.equal((await api('/rewards'))[0].image_uri, 'test-image');
    assert.equal((await api(`/rewards/${reward.id}/redeem`, {})).success, true);
    const redemptions = await api('/rewards/redemptions');
    assert.equal(redemptions.length, 1);
    await api(`/rewards/redemptions/${redemptions[0].id}/complete`, {});
    assert.equal((await api('/rewards/history')).length, 1);
    assert.equal((await api('/stats/equity'))[0].points, 20);
    await api('/users/vacation', { is_on_vacation: true });
    assert.equal((await api('/users/dashboard')).is_on_vacation, true);
    console.log('PASS: production startup, registration, login, group creation, task completion, reward visuals/redemption/history, equity and vacation.');
  } finally {
    if (server) {
      server.kill('SIGTERM');
      await new Promise(resolve => { if (server.exitCode !== null) resolve(); else server.once('exit', resolve); });
    }
    if (databaseStarted) execFileSync(path.join(pg, 'pg_ctl'), ['-D', data, '-m', 'fast', '-w', 'stop'], { stdio: 'pipe' });
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
