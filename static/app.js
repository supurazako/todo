const $ = id => document.getElementById(id);
let data = [], owner = false, filter = 'open';
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {method, credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  if (!response.ok) {
    if (response.status === 401) { $('login').hidden = false; $('workspace').hidden = true; $('logout').hidden = true; }
    throw new Error(response.status === 401 ? 'キーが無効、またはログインの有効期限が切れています。' : response.status === 429 ? 'しばらく待ってから再度お試しください。' : '操作を完了できませんでした。再度お試しください。');
  }
  return response.json();
}
function report(error) { $('message').textContent = error.message; }
function button(label, action, className = '') {
  const el = document.createElement('button'); el.type = 'button'; el.textContent = label; el.className = className;
  el.onclick = async () => { el.disabled = true; try { await action(); $('message').textContent = ''; } catch (e) { report(e); } finally { el.disabled = false; } }; return el;
}
function render() {
  $('list').replaceChildren();
  $('openTab').setAttribute('aria-pressed', String(filter === 'open'));
  $('doneTab').setAttribute('aria-pressed', String(filter === 'completed'));
  const items = data.filter(item => item.status === filter); $('empty').hidden = items.length !== 0;
  for (const item of items) {
    const li = document.createElement('li');
    const text = document.createElement('span'); text.className = 'tasktext'; text.textContent = item.task;
    if (owner) {
      const check = document.createElement('input'); check.type = 'checkbox'; check.checked = item.status === 'completed'; check.setAttribute('aria-label', `${item.task}：完了状態`);
      check.onchange = async () => { check.disabled = true; try { await api(`/api/todos/${item.id}`, 'PATCH', {status: check.checked ? 'completed' : 'open'}); await load(); } catch(e) { check.checked = !check.checked; report(e); } finally {check.disabled = false;} }; li.append(check);
    }
    li.append(text);
    if (owner) {
      const actions = document.createElement('div'); actions.className = 'actions';
      actions.append(button('編集', async () => { const task = prompt('TODOを編集', item.task); if (task !== null) { await api(`/api/todos/${item.id}`, 'PATCH', {task}); await load(); } }), button('削除', async () => { if (confirm('このTODOを削除しますか？')) { await api(`/api/todos/${item.id}`, 'DELETE'); await load(); } }, 'danger')); li.append(actions);
    }
    $('list').append(li);
  }
}
async function load() { const result = await api('/api/todos'); data = result.todos; owner = result.role === 'owner'; $('login').hidden = true; $('workspace').hidden = false; $('logout').hidden = false; $('addForm').hidden = !owner; $('role').textContent = owner ? '所有者 · 編集できます' : '閲覧専用'; render(); }
$('loginForm').onsubmit = async event => { event.preventDefault(); try { await api('/api/login', 'POST', {key: $('key').value}); $('key').value = ''; $('message').textContent = ''; await load(); } catch(e) {report(e);} };
$('addForm').onsubmit = async event => { event.preventDefault(); const submit = event.submitter; submit.disabled = true; try { await api('/api/todos', 'POST', {task: $('task').value}); $('task').value = ''; $('message').textContent = ''; await load(); } catch(e) {report(e);} finally {submit.disabled = false;} };
$('logout').onclick = async () => { try {await api('/api/logout', 'POST', {}); location.reload();} catch(e) {report(e);} };
$('openTab').onclick = () => { filter = 'open'; render(); };
$('doneTab').onclick = () => { filter = 'completed'; render(); };
load().catch(error => { if (!$('workspace').hidden) report(error); });
