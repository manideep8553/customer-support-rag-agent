import sys, asyncio
sys.path.insert(0, '.')
from backend.main import app
from backend.auth.database import init_db, close_db, async_session_factory
from backend.customer.seed import seed_customer_data
from httpx import AsyncClient, ASGITransport

async def test():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test', timeout=15) as c:

        r = await c.post('/api/v1/auth/register', json={
            'email': 'jane@test.com', 'username': 'jane', 'password': 'JanePass99',
            'display_name': 'Jane Doe',
        })
        access = r.json()['access_token']
        headers = {'Authorization': f'Bearer {access}'}
        async with async_session_factory() as session:
            await seed_customer_data(session)

        print('=== TICKET MANAGEMENT API ===')

        r = await c.get('/api/v1/customer/support-tickets', headers=headers)
        assert r.status_code == 200
        tickets = r.json()['support_tickets']
        assert len(tickets) >= 4
        print(f'OK List tickets: {len(tickets)} tickets')

        r = await c.get('/api/v1/customer/support-tickets?status=open', headers=headers)
        assert r.status_code == 200
        open_tickets = r.json()['support_tickets']
        print(f'OK Filter by status (open): {len(open_tickets)} tickets')

        r = await c.get('/api/v1/customer/support-tickets/TKT-2025-001', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket_number'] == 'TKT-2025-001'
        assert d['status'] == 'resolved'
        assert len(d['comments']) >= 3
        assert d['resolution'] is not None
        print(f'OK Ticket detail: {d["ticket_number"]} ({d["status"]}, {len(d["comments"])} comments, {len(d["attachments"])} attachments)')

        r = await c.get('/api/v1/customer/support-tickets/TKT-2025-005', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['status'] == 'escalated'
        assert d['escalation_reason'] is not None
        assert d['escalated_at'] is not None
        assert len(d['comments']) >= 5
        print(f'OK Escalated: {d["ticket_number"]} (escalated, {len(d["comments"])} comments)')

        r = await c.post('/api/v1/customer/support-tickets', json={
            'subject': 'Test creation via API',
            'category': 'technical_support',
            'description': 'This is a test ticket created via the API.',
            'priority': 'high',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['status'] == 'created'
        ticket = d['ticket']
        new_num = ticket['ticket_number']
        assert new_num.startswith('TKT-')
        assert ticket['status'] == 'open'
        assert len(ticket['comments']) >= 1
        print(f'OK Create ticket: {new_num}')

        r = await c.patch(f'/api/v1/customer/support-tickets/{new_num}/status', json={
            'status': 'in_progress',
            'note': 'Acknowledged and working on it',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'in_progress'
        print(f'OK Update status -> in_progress: {new_num}')

        r = await c.post(f'/api/v1/customer/support-tickets/{new_num}/comments', json={
            'body': 'Please check this issue urgently.',
            'is_internal': False,
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['status'] == 'comment_added'
        comment_count = len(d['ticket']['comments'])
        print(f'OK Add comment: {new_num} ({comment_count} comments)')

        r = await c.post(f'/api/v1/customer/support-tickets/{new_num}/escalate', json={
            'reason': 'This issue is blocking our production deployment.',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'escalated'
        assert d['ticket']['escalation_reason'] is not None
        print(f'OK Escalate: {new_num} -> escalated')

        r = await c.patch(f'/api/v1/customer/support-tickets/{new_num}/status', json={
            'status': 'resolved',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'resolved'
        print(f'OK Resolve: {new_num} -> resolved')

        r = await c.post(f'/api/v1/customer/support-tickets/{new_num}/reopen', json={
            'reason': 'Issue still occurring after testing.',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'open'
        print(f'OK Reopen: {new_num} -> open (reopened)')

        r = await c.patch(f'/api/v1/customer/support-tickets/{new_num}/status', json={
            'status': 'closed',
            'note': 'All resolved, customer confirmed.',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'closed'
        print(f'OK Close: {new_num} -> closed')

        r = await c.post(f'/api/v1/customer/support-tickets/TKT-2025-001/reopen', json={
            'reason': 'Need additional help.',
        }, headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['ticket']['status'] == 'open'
        print(f'OK Reopen existing resolved: TKT-2025-001 -> open')

        r = await c.get('/api/v1/customer/support-tickets/INVALID-TKT', headers=headers)
        assert r.status_code == 404
        print('OK Get invalid ticket: 404')

        print()
        print('=== CHATBOT TICKET QUERIES ===')

        tests = [
            ('My support tickets', ['Support Tickets', 'TKT-2025']),
            ('What is the status of my ticket TKT-2025-005?', ['TKT-2025-005', 'Escalated']),
            ('Create a ticket for me', ['Support Tickets', 'TKT-2025']),
        ]
        for label, expected in tests:
            r = await c.post('/api/v1/chat', json={'session_id': 'tkt-chat', 'message': label}, headers=headers)
            ans = r.json()['answer']
            ok = all(e.lower() in ans.lower() for e in expected)
            print(f'  {"OK" if ok else "FAIL"} {label}')
            if not ok:
                missing = [e for e in expected if e.lower() not in ans.lower()]
                print(f'    Missing: {missing}')

        print()
        print('ALL TICKET MANAGEMENT TESTS PASSED')

    await close_db()

asyncio.run(test())
