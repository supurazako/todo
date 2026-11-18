import pytest
from test_app import settings, client, login, ORIGIN

@pytest.mark.parametrize('method,path', [('post','/api/todos'),('patch','/api/todos/1'),('delete','/api/todos/1'),('post','/api/finance'),('put','/api/finance/1'),('delete','/api/finance/1')])
def test_public_cannot_write(client,method,path):
    assert getattr(client,method)(path,json={},headers=ORIGIN).status_code==401

def test_public_reads_existing_records(client):
    login(client)
    client.post('/api/todos',json={'task':'public task'},headers=ORIGIN)
    client.post('/api/finance',json=dict(kind='expense',title='public entry',amount=100,occurred_on='2026-11-18'),headers=ORIGIN)
    client.post('/api/logout',json={},headers=ORIGIN)
    assert client.get('/api/todos').json['todos'][0]['task']=='public task'
    result=client.get('/api/finance?month=2026-11').json
    assert result['entries'][0]['title']=='public entry'
    assert result['summary']['expense']==100
