import sqlite3
import pytest
from test_app import settings, client, login, ORIGIN
from app import create_app

ENTRY = dict(kind='expense',title='食費',amount=1250,occurred_on='2026-11-18')

def test_finance_owner_crud_and_month(client, settings):
    login(client)
    created=client.post('/api/finance',json=ENTRY,headers=ORIGIN)
    assert created.status_code==201
    ident=created.json['id']
    assert client.post('/api/finance',json={**ENTRY,'kind':'income','amount':10000},headers=ORIGIN).status_code==201
    assert client.post('/api/finance',json={**ENTRY,'occurred_on':'2026-12-01','amount':999},headers=ORIGIN).status_code==201
    r=client.get('/api/finance?month=2026-11').json
    assert len(r['entries'])==2
    assert r['summary']=={'income':10000,'expense':1250,'net':8750}
    changed={**ENTRY,'amount':3000,'title':'変更'}
    assert client.put(f'/api/finance/{ident}',json=changed,headers=ORIGIN).status_code==200
    fresh=create_app(settings).test_client();login(fresh)
    assert fresh.get('/api/finance?month=2026-11').json['summary']['net']==7000
    assert fresh.delete(f'/api/finance/{ident}',json={},headers=ORIGIN).status_code==200
    rows=fresh.get('/api/finance?month=2026-11').json['entries']
    assert all(r['id']!=ident for r in rows)
    # Existing reminder schema/data remain valid.
    with sqlite3.connect(settings['DATABASE']) as db:
        assert db.execute("SELECT task FROM todo_items WHERE status='open' ORDER BY todo_id").fetchall()==[]

@pytest.mark.parametrize('method,path,payload', [('post','/api/finance',ENTRY),('put','/api/finance/1',ENTRY),('delete','/api/finance/1',{})])
def test_viewer_finance_read_only(client,method,path,payload):
    login(client)
    client.post('/api/finance',json=ENTRY,headers=ORIGIN)
    login(client,'viewer-key')
    r=client.get('/api/finance?month=2026-11')
    assert r.status_code==200 and r.json['entries'][0]['title']=='食費'
    assert getattr(client,method)(path,json=payload,headers=ORIGIN).status_code==403
    assert client.get('/api/finance?month=2026-11').json['summary']['expense']==1250

@pytest.mark.parametrize('field,value',[('amount',0),('amount',-1),('amount',True),('amount',1.5),('amount','100'),('amount',1000000001),('kind','other'),('title',''),('occurred_on','2026-02-30'),('occurred_on','20261118'),('occurred_on','0000-01-01')])
def test_finance_validation(client,field,value):
    login(client)
    assert client.post('/api/finance',json={**ENTRY,field:value},headers=ORIGIN).status_code==400
    assert client.get('/api/finance?month=2026-11').json['entries']==[]

@pytest.mark.parametrize('month',['2026-13','0000-01','2026-1','x',"2026-11' OR 1=1"])
def test_month_validation(client,month):
    login(client)
    assert client.get('/api/finance',query_string={'month':month}).status_code==400

def test_finance_anonymous_and_origin(client):
    assert client.get('/api/finance?month=2026-11').status_code==200
    assert client.post('/api/finance',json=ENTRY,headers=ORIGIN).status_code==401
    login(client)
    assert client.post('/api/finance',json=ENTRY,headers={'Origin':'https://evil.example'}).status_code==403
    assert client.put('/api/finance/999',json=ENTRY,headers=ORIGIN).status_code==404
    assert client.delete('/api/finance/999',json={},headers=ORIGIN).status_code==404
