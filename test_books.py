import sqlite3
import pytest
from test_app import settings,client,ORIGIN

def test_public_books_sorted_and_rereads(client,settings):
    with sqlite3.connect(settings['DATABASE']) as con:
        con.executemany('INSERT INTO reading_books(finished_on,title,author) VALUES (?,?,?)',[
            ('2026-11-01','同じ本','著者'),('2026-11-18','同じ本','著者'),('2026-11-18','別の本','別の著者')])
    r=client.get('/api/books')
    assert r.status_code==200
    assert [x['title'] for x in r.json['books']]==['別の本','同じ本','同じ本']
    assert 'noindex' in r.headers['X-Robots-Tag']
    assert set(r.json['books'][0])=={'id','title','author','finished_on'}

@pytest.mark.parametrize('method,path',[('post','/api/books'),('put','/api/books/1'),('patch','/api/books/1'),('delete','/api/books/1')])
def test_no_web_write_books(client,method,path):
    assert getattr(client,method)(path,json={},headers=ORIGIN).status_code in (404,405)

def test_books_empty(client):
    assert client.get('/api/books').json=={'books':[]}
