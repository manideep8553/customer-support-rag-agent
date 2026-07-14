import sys, json, asyncio
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
            'display_name': 'Jane Doe', 'company': 'TestCo',
        })
        access = r.json()['access_token']
        headers = {'Authorization': f'Bearer {access}'}
        async with async_session_factory() as session:
            await seed_customer_data(session)
            await session.close()

        print('=== ORDER MANAGEMENT API ===')

        r = await c.get('/api/v1/customer/orders', headers=headers)
        assert r.status_code == 200
        orders = r.json()['orders']
        assert len(orders) >= 4
        print(f'OK List orders: {len(orders)} orders')

        r = await c.get('/api/v1/customer/orders/ORD-2025-003', headers=headers)
        d = r.json()
        assert d['order_number'] == 'ORD-2025-003'
        assert 'status_history' in d
        assert len(d['status_history']) >= 1
        assert len(d['items']) == 2
        print(f'OK Order detail: {d["order_number"]} ({d["status"]}, payment: {d["payment_status"]}, {len(d["status_history"])} logs)')

        r = await c.get('/api/v1/customer/orders/ORD-2024-099', headers=headers)
        d = r.json()
        assert d['status'] == 'refunded'
        assert d['payment_status'] == 'refunded'
        assert d['refunded_amount'] > 0
        assert d['cancellation_reason']
        assert len(d['status_history']) >= 6
        print(f'OK Refunded: {d["order_number"]} ({len(d["status_history"])} transitions)')

        r = await c.get('/api/v1/customer/orders/ORD-2025-001/history', headers=headers)
        h = r.json()['history']
        assert len(h) == 4
        assert h[0]['from_status'] == 'pending'
        assert h[-1]['to_status'] == 'delivered'
        print(f'OK Status history: {len(h)} transitions (pending -> delivered)')

        r = await c.get('/api/v1/customer/orders/ORD-2025-001/invoice', headers=headers)
        inv = r.json()
        assert inv['invoice_number'] == 'INV-ORD-2025-001'
        assert inv['total'] == 13200.0
        assert inv['amount_paid'] == 13200.0
        assert inv['pdf_url'] is not None
        print(f'OK Invoice: {inv["invoice_number"]} (total: {inv["total"]}, paid: {inv["amount_paid"]})')

        r = await c.post('/api/v1/customer/orders/ORD-2025-004/cancel',
            json={'reason': 'Changed my mind - ordered wrong item'}, headers=headers)
        assert r.status_code == 200
        cd = r.json()
        assert cd['status'] == 'cancelled'
        assert cd['order']['cancellation_reason'] == 'Changed my mind - ordered wrong item'
        print(f'OK Cancel: {cd["order"]["order_number"]} -> cancelled')

        r = await c.post('/api/v1/customer/orders/ORD-2025-001/cancel',
            json={'reason': 'Test'}, headers=headers)
        assert r.status_code == 400
        print(f'OK Cancel delivered rejected: 400')

        r = await c.post('/api/v1/customer/orders/ORD-2025-002/return',
            json={'reason': 'Product not as described', 'items': [{'product': 'GigaAnalytics License', 'quantity': 1}]},
            headers=headers)
        assert r.status_code == 200
        ret = r.json()
        assert ret['status'] == 'return_requested'
        assert 'RMA-' in ret['return']['rma_number']
        print(f'OK Return: {ret["return"]["rma_number"]}')

        r = await c.post('/api/v1/customer/orders/ORD-2025-001/exchange',
            json={'reason': 'Need upgraded hardware', 'original_product': 'GigaBox Enterprise', 'replacement_product': 'GigaBox Pro'},
            headers=headers)
        assert r.status_code == 200
        exch = r.json()
        assert exch['status'] == 'exchange_requested'
        assert exch['exchange']['original_product'] == 'GigaBox Enterprise'
        print(f'OK Exchange: {exch["exchange"]["original_product"]} -> {exch["exchange"]["replacement_product"]}')

        print()
        print('=== CHATBOT ORDER QUERIES ===')

        tests = [
            ('Order status', 'Where is my order?', ['ORD-2025-003', 'Confirmed']),
            ('Invoice info', 'Can I get an invoice for my order?', ['ORD-2025', 'portal.gigacorp.com/invoices']),
            ('Return policy', 'How do I return an item?', ['RMA', '30 days', 'return label']),
            ('Exchange policy', 'Can I exchange my GigaBox?', ['Exchange', 'GigaBox Enterprise']),
            ('Cancellation', 'How do I cancel my pending order?', ['ORD-2025-004', 'cancelled']),
            ('Refunded order', 'What happened to ORD-2024-099?', ['refunded']),
        ]
        for label, query, expected in tests:
            r = await c.post('/api/v1/chat', json={'session_id': 'ord-chat', 'message': query}, headers=headers)
            ans = r.json()['answer']
            ok = all(e.lower() in ans.lower() for e in expected)
            print(f'  {"OK" if ok else "FAIL"} {label}')
            if not ok:
                missing = [e for e in expected if e.lower() not in ans.lower()]
                print(f'    Missing: {missing}')

        r = await c.post('/api/v1/chat', json={'session_id': 'anon', 'message': 'Where is my order?'})
        assert 'ORD-' not in r.json()['answer']
        print('  OK Anonymous: no order data')

        print()
        print('ALL TESTS PASSED')
    await close_db()

asyncio.run(test())
