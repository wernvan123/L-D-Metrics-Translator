import json


def test_create_list_get_update_delete_framework(client, auth_headers):
    # Create
    payload = {
        'name': 'Leadership 2025',
        'description': 'Core leadership capabilities',
        'source': 'Internal',
        'is_builtin': False,
        'is_active': True,
        'sort_order': 1,
    }
    resp = client.post('/api/frameworks', data=json.dumps(payload), headers=auth_headers)
    assert resp.status_code == 201
    fw = resp.get_json()['framework']
    fw_id = fw['id']
    assert fw['name'] == 'Leadership 2025'

    # List
    resp = client.get('/api/frameworks')
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(f['id'] == fw_id for f in data['frameworks'])

    # Get with include
    resp = client.get(f'/api/frameworks/{fw_id}?include=competencies,metrics')
    assert resp.status_code == 200
    got = resp.get_json()['framework']
    assert got['id'] == fw_id

    # Update name and slug
    resp = client.patch(
        f'/api/frameworks/{fw_id}',
        data=json.dumps({'name': 'Leadership 2030', 'slug': 'leadership-2030'}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.get_json()['framework']
    assert updated['name'] == 'Leadership 2030'
    assert updated['slug'] == 'leadership-2030'

    # Soft delete
    resp = client.delete(f'/api/frameworks/{fw_id}', headers=auth_headers)
    assert resp.status_code == 200

    # List active should exclude now-inactive
    resp = client.get('/api/frameworks?active=true')
    assert resp.status_code == 200
    active_list = resp.get_json()['frameworks']
    assert not any(f['id'] == fw_id for f in active_list)

    # Hard delete
    resp = client.delete(f'/api/frameworks/{fw_id}?hard=true', headers=auth_headers)
    assert resp.status_code == 200
