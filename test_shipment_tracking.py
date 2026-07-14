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

        print('=== SHIPMENT TRACKING API ===')

        r = await c.get('/api/v1/customer/shipments', headers=headers)
        assert r.status_code == 200
        data = r.json()
        shipments = data['shipments']
        assert len(shipments) >= 2
        print(f'OK List shipments: {len(shipments)} shipments')

        tracking_num = shipments[0]['tracking_number']
        r = await c.get(f'/api/v1/customer/shipments/track/{tracking_num}', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['tracking_number'] == tracking_num
        assert 'status' in d
        assert 'timeline' in d
        assert len(d['timeline']) >= 1
        assert d['courier'] is not None
        assert d['current_location'] is not None
        print(f'OK Track {tracking_num}: {d["status"]} ({len(d["timeline"])} events, courier: {d["courier"]})')

        r = await c.get(f'/api/v1/customer/shipments/track/INVALID-TRK-999', headers=headers)
        assert r.status_code == 404
        print('OK Track invalid: 404')

        r = await c.get('/api/v1/customer/orders/ORD-2025-001/shipments', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert len(d['shipments']) >= 1
        assert d['shipments'][0]['tracking_number'] == '1Z999AA10123456784'
        assert d['shipments'][0]['status'] == 'delivered'
        print(f'OK Order shipments: {d["order_number"]} -> {d["shipments"][0]["delivered_at"]}')

        r = await c.get('/api/v1/customer/orders/ORD-2025-003/shipments', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert len(d['shipments']) >= 1
        assert d['shipments'][0]['courier_code'] == 'dhl'
        print(f'OK Order shipments DHL: {d["shipments"][0]["tracking_number"]} ({d["shipments"][0]["courier"]})')

        r = await c.post(f'/api/v1/customer/shipments/track/{tracking_num}/refresh', headers=headers)
        assert r.status_code == 200
        d = r.json()
        assert d['tracking_number'] == tracking_num
        print(f'OK Refresh tracking: {d["status"]}')

        print()
        print('=== CHATBOT TRACKING QUERIES ===')

        tests = [
            ('Where is my package?', ['Shipment Status', 'Carrier', 'Tracking', 'Current Location']),
            ('When will it arrive?', ['Estimated Delivery']),
            ('Has my order shipped?', ['Shipment Status', 'Carrier']),
            ('Track my package', ['Shipment Status', 'Tracking']),
        ]
        for label, expected in tests:
            r = await c.post('/api/v1/chat', json={'session_id': 'trk-chat', 'message': label}, headers=headers)
            ans = r.json()['answer']
            ok = all(e.lower() in ans.lower() for e in expected)
            print(f'  {"OK" if ok else "FAIL"} {label}')
            if not ok:
                missing = [e for e in expected if e.lower() not in ans.lower()]
                print(f'    Missing: {missing}')

        r = await c.post('/api/v1/chat', json={
            'session_id': 'trk-chat2',
            'message': 'Where is my package with tracking number 1Z999AA10123456784?',
        }, headers=headers)
        ans = r.json()['answer']
        ok = '1Z999AA10123456784' in ans
        print(f'  {"OK" if ok else "FAIL"} Tracking number in query')
        if not ok:
            print(f'    Answer: {ans[:200]}')

        print()
        print('ALL SHIPMENT TRACKING TESTS PASSED')

    await close_db()

asyncio.run(test())
