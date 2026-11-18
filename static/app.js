const $ = id => document.getElementById(id);
let data = [], entries = [], owner = false, filter = 'open', loggedIn = false, editId = null, editTaskId = null;
const money = value => new Intl.NumberFormat('ja-JP', {style: 'currency', currency: 'JPY'}).format(value);
function localDate() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
$('month').value = localDate().slice(0,7);
function signedOut() {
  loggedIn = false; data = []; entries = []; owner = false;
  $('login').hidden = false; $('workspace').hidden = true; $('logout').hidden = true; $('financeNav').hidden = true; $('role').textContent = '未接続';
  $('list').replaceChildren(); $('entries').replaceChildren();
  for (const id of ['income','expense','net']) $(id).textContent = '—';
  for (const id of ['entryDialog','taskDialog']) if ($(id).open) $(id).close();
}
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {method, credentials:'same-origin', headers:{'Content-Type':'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  if (!response.ok) {
    if (response.status === 401) signedOut();
    throw new Error(response.status === 401 ? 'キーが無効、またはログインの有効期限が切れています。' : response.status === 429 ? 'しばらく待ってから再度お試しください。' : response.status === 400 ? '入力内容を確認してください。金額は1円以上の整数で入力してください。' : '操作を完了できませんでした。再度お試しください。');
  }
  return response.json();
}
function report(error) { $('message').textContent = error.message; }
function button(label, action, className='') {
  const el = document.createElement('button'); el.type = 'button'; el.textContent = label; el.className = className;
  el.onclick = async () => { el.disabled = true; try {await action(); $('message').textContent='';} catch(e){report(e);} finally {el.disabled=false;} }; return el;
}
function closeMenu() { $('sidebar').classList.remove('open'); $('menu').setAttribute('aria-expanded','false'); }
async function route() {
  closeMenu(); if (!loggedIn) return;
  const finance = location.hash === '#finance';
  $('todoView').hidden = finance; $('financeView').hidden = !finance;
  $('todoNav').setAttribute('aria-current',finance ? 'false' : 'page'); $('financeNav').setAttribute('aria-current',finance ? 'page' : 'false');
  if (finance) await loadFinance();
}
function render() {
  $('list').replaceChildren();
  $('todoCount').textContent = `${data.filter(x => x.status === 'open').length} 件の未完了`;
  $('openTab').setAttribute('aria-pressed',String(filter === 'open')); $('doneTab').setAttribute('aria-pressed',String(filter === 'completed'));
  const items = data.filter(x => x.status === filter); $('empty').hidden = items.length !== 0;
  for (const item of items) {
    const li = document.createElement('li'); if(item.status === 'completed') li.className = 'completed';
    const text = document.createElement('span'); text.className='tasktext'; text.textContent=item.task;
    if(owner) {
      const check = document.createElement('input'); check.type='checkbox'; check.checked=item.status === 'completed'; check.setAttribute('aria-label',`${item.task}：完了状態`);
      check.onchange = async () => { check.disabled=true; try {await api(`/api/todos/${item.id}`,'PATCH',{status:check.checked?'completed':'open'}); await loadTodos();} catch(e){check.checked=!check.checked;report(e);} finally{check.disabled=false;} }; li.append(check);
    }
    li.append(text);
    if(owner) {
      const actions=document.createElement('div'); actions.className='actions';
      actions.append(button('編集',()=>{editTaskId=item.id; $('editTask').value=item.task; $('taskError').textContent=''; $('taskDialog').showModal();}),button('削除',async()=>{if(confirm('このTODOを削除しますか？')){await api(`/api/todos/${item.id}`,'DELETE',{}); await loadTodos();}},'danger')); li.append(actions);
    }
    $('list').append(li);
  }
}
async function loadTodos() {
  const result=await api('/api/todos'); data=result.todos; owner=result.role==='owner'; loggedIn=true;
  $('login').hidden=true; $('workspace').hidden=false; $('logout').hidden=false; $('financeNav').hidden=false;
  $('addForm').hidden=!owner; $('newEntry').hidden=!owner; $('role').textContent=owner?'所有者 · 編集可能':'閲覧専用 · Todo / 家計簿'; render();
}
async function loadFinance() {
  const month=$('month').value; if(!month) return;
  $('entries').replaceChildren(); $('financeEmpty').hidden=true;
  for(const id of ['income','expense','net']) $(id).textContent='—';
  const result=await api(`/api/finance?month=${encodeURIComponent(month)}`);
  if ($('month').value !== month || !loggedIn) return;
  entries=result.entries;
  for(const id of ['income','expense','net']) $(id).textContent=money(result.summary[id]);
  $('net').className=result.summary.net<0?'expense':'income'; $('entryCount').textContent=`${entries.length} 件`; $('financeEmpty').hidden=entries.length!==0;
  for(const item of entries) {
    const li=document.createElement('li'), body=document.createElement('div'), title=document.createElement('strong'), date=document.createElement('small'), amount=document.createElement('span');
    body.className='entrybody'; title.textContent=item.title; date.textContent=`${item.occurred_on} · ${item.kind==='income'?'収入':'支出'}`; body.append(title,date);
    amount.className=`entryamount ${item.kind}`; amount.textContent=`${item.kind==='income'?'+':'−'}${money(item.amount)}`; li.append(body,amount);
    if(owner) {const actions=document.createElement('div'); actions.className='actions'; actions.append(button('編集',()=>openEntry(item)),button('削除',async()=>{if(confirm('この収支記録を削除しますか？')){await api(`/api/finance/${item.id}`,'DELETE',{});await loadFinance();}},'danger'));li.append(actions);}
    $('entries').append(li);
  }
}
function openEntry(item=null) {
  if(!owner) return;
  editId=item?.id??null; $('entryHeading').textContent=item?'収支を編集':'収支を記録';
  $('kind').value=item?.kind??'expense'; $('occurred').value=item?.occurred_on??localDate(); $('entryTitle').value=item?.title??''; $('amount').value=item?.amount??''; $('entryError').textContent=''; $('entryDialog').showModal();
}
$('loginForm').onsubmit=async event=>{event.preventDefault();const submit=event.submitter;submit.disabled=true;try{await api('/api/login','POST',{key:$('key').value});$('key').value='';$('message').textContent='';await loadTodos();await route();}catch(e){report(e);}finally{submit.disabled=false;}};
$('addForm').onsubmit=async event=>{event.preventDefault();const submit=event.submitter;submit.disabled=true;try{await api('/api/todos','POST',{task:$('task').value});$('task').value='';$('message').textContent='';await loadTodos();}catch(e){report(e);}finally{submit.disabled=false;}};
$('taskEditForm').onsubmit=async event=>{event.preventDefault();const submit=event.submitter;submit.disabled=true;try{await api(`/api/todos/${editTaskId}`,'PATCH',{task:$('editTask').value});$('taskDialog').close();await loadTodos();}catch(e){$('taskError').textContent=e.message;}finally{submit.disabled=false;}};
$('entryForm').onsubmit=async event=>{event.preventDefault();$('saveEntry').disabled=true;try{const payload={kind:$('kind').value,title:$('entryTitle').value,amount:Number($('amount').value),occurred_on:$('occurred').value};await api(editId===null?'/api/finance':`/api/finance/${editId}`,editId===null?'POST':'PUT',payload);$('month').value=payload.occurred_on.slice(0,7);$('entryDialog').close();await loadFinance();}catch(e){$('entryError').textContent=e.message;}finally{$('saveEntry').disabled=false;}};
$('logout').onclick=async()=>{try{await api('/api/logout','POST',{});signedOut();closeMenu();}catch(e){report(e);}};
$('openTab').onclick=()=>{filter='open';render();}; $('doneTab').onclick=()=>{filter='completed';render();};
$('newEntry').onclick=()=>openEntry();
$('closeEntry').onclick=$('cancelEntry').onclick=()=>$('entryDialog').close(); $('cancelTask').onclick=()=>$('taskDialog').close();
$('month').onchange=()=>loadFinance().catch(report);
function moveMonth(delta){const value=$('month').value;if(!value)return;let [year,month]=value.split('-').map(Number);month+=delta;if(month===0){year--;month=12;}if(month===13){year++;month=1;}if(year<1||year>9999)return;$('month').value=`${String(year).padStart(4,'0')}-${String(month).padStart(2,'0')}`;loadFinance().catch(report);}
$('prevMonth').onclick=()=>moveMonth(-1);$('nextMonth').onclick=()=>moveMonth(1);
$('menu').onclick=()=>{const open=$('sidebar').classList.toggle('open');$('menu').setAttribute('aria-expanded',String(open));};
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();});
window.addEventListener('hashchange',()=>route().catch(report));
loadTodos().then(route).catch(error=>{if(loggedIn)report(error);});
