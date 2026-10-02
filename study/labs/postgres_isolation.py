"""Bounded PostgreSQL 17 lab; creates/removes only its own UUID schema."""
import argparse
import json
import platform
from pathlib import Path
import uuid

import psycopg
from psycopg import sql


def run(port):
    schema = 'study_' + uuid.uuid4().hex
    conns = []
    result = {'python': platform.python_version(), 'psycopg': psycopg.__version__, 'cases': {}}
    def connect():
        c = psycopg.connect(host='127.0.0.1', port=port, dbname='study', user='postgres',
                            connect_timeout=3, autocommit=True)
        conns.append(c)
        c.execute('SET statement_timeout = 5000')
        c.execute('SET lock_timeout = 500')
        c.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
        return c
    admin = connect()
    created = False
    try:
        result['server'] = admin.execute('SELECT version()').fetchone()[0]
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        created = True
        admin.execute('CREATE TABLE counter (id integer PRIMARY KEY, value integer NOT NULL)')
        admin.execute('INSERT INTO counter VALUES (1, 100)')
        admin.execute('CREATE TABLE doctors (id integer PRIMARY KEY, on_call boolean NOT NULL)')
        admin.execute('INSERT INTO doctors VALUES (1,true),(2,true)')
        a, b = connect(), connect()
        for level, expected in [('READ COMMITTED', [100, 200]), ('REPEATABLE READ', [100, 100])]:
            admin.execute('UPDATE counter SET value=100')
            a.execute('BEGIN ISOLATION LEVEL ' + level)  # fixed values above, no user SQL
            first = a.execute('SELECT value FROM counter WHERE id=1').fetchone()[0]
            b.execute('UPDATE counter SET value=200 WHERE id=1')
            second = a.execute('SELECT value FROM counter WHERE id=1').fetchone()[0]
            a.execute('COMMIT')
            assert [first, second] == expected
            result['cases'][level] = [first, second]
        admin.execute('UPDATE counter SET value=100')
        a.execute('BEGIN'); b.execute('BEGIN')
        av = a.execute('SELECT value FROM counter').fetchone()[0]
        bv = b.execute('SELECT value FROM counter').fetchone()[0]
        a.execute('UPDATE counter SET value=%s', (av+1,)); a.execute('COMMIT')
        b.execute('UPDATE counter SET value=%s', (bv+1,)); b.execute('COMMIT')
        lost = admin.execute('SELECT value FROM counter').fetchone()[0]
        assert lost == 101
        result['cases']['stale_read_modify_write'] = lost
        admin.execute('UPDATE counter SET value=100')
        a.execute('UPDATE counter SET value=value+1'); b.execute('UPDATE counter SET value=value+1')
        atomic = admin.execute('SELECT value FROM counter').fetchone()[0]
        assert atomic == 102
        result['cases']['server_side_increment'] = atomic
        for level in ['REPEATABLE READ', 'SERIALIZABLE']:
            admin.execute('UPDATE doctors SET on_call=true')
            a.execute('BEGIN ISOLATION LEVEL ' + level); b.execute('BEGIN ISOLATION LEVEL ' + level)
            counts = [c.execute('SELECT count(*) FROM doctors WHERE on_call').fetchone()[0] for c in (a,b)]
            assert counts == [2,2]
            a.execute('UPDATE doctors SET on_call=false WHERE id=1')
            b.execute('UPDATE doctors SET on_call=false WHERE id=2')
            a.execute('COMMIT')
            code = None
            try:
                b.execute('COMMIT')
            except psycopg.Error as exc:
                code = exc.sqlstate
                b.execute('ROLLBACK')
            remaining = admin.execute('SELECT count(*) FROM doctors WHERE on_call').fetchone()[0]
            if level == 'REPEATABLE READ':
                assert code is None and remaining == 0
            else:
                assert code == '40001' and remaining == 1
                # Retry the entire decision, not the failed UPDATE alone.
                b.execute('BEGIN ISOLATION LEVEL SERIALIZABLE')
                count = b.execute('SELECT count(*) FROM doctors WHERE on_call').fetchone()[0]
                if count > 1:
                    b.execute('UPDATE doctors SET on_call=false WHERE id=2')
                b.execute('COMMIT')
                assert admin.execute('SELECT count(*) FROM doctors WHERE on_call').fetchone()[0] == 1
            result['cases']['write_skew_' + level] = {'initial_counts': counts, 'remaining': remaining, 'sqlstate': code}
        a.execute('BEGIN'); a.execute('SELECT * FROM counter WHERE id=1 FOR UPDATE')
        b.execute('BEGIN'); b.execute('SET LOCAL lock_timeout = 100')
        try:
            b.execute('UPDATE counter SET value=value+1 WHERE id=1')
            raise AssertionError('Expected lock timeout')
        except psycopg.Error as exc:
            assert exc.sqlstate == '55P03'
            result['cases']['lock_timeout_sqlstate'] = exc.sqlstate
        finally:
            b.execute('ROLLBACK'); a.execute('ROLLBACK')
        admin.execute('CREATE TABLE orders AS SELECT g AS id, g % 1000 AS user_id, g AS created_at, repeat(\'x\',80) AS payload FROM generate_series(1,100000) AS g')
        admin.execute('ANALYZE orders')
        query = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT id, created_at FROM orders WHERE user_id=42 ORDER BY created_at DESC LIMIT 20'
        before = admin.execute(query).fetchone()[0][0]
        admin.execute('CREATE INDEX orders_user_time ON orders(user_id, created_at DESC)')
        admin.execute('ANALYZE orders')
        after = admin.execute(query).fetchone()[0][0]
        assert before['Plan']['Actual Rows'] == after['Plan']['Actual Rows'] == 20
        result['index'] = {'rows': 100000, 'before': before, 'after': after}
        result['validation'] = '7 isolation/locking cases and before/after query returned expected results'
    finally:
        for c in conns[1:]:
            c.close()
        if created:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
            assert admin.execute('SELECT count(*) FROM pg_namespace WHERE nspname=%s', (schema,)).fetchone()[0] == 0
        admin.close()
    result['cleanup'] = 'own UUID schema dropped; all connections closed'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.output.exists():
        parser.error('Use valid loopback port and a new output path')
    result = run(args.port)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'cases': result['cases'], 'cleanup': result['cleanup']}, indent=2))
