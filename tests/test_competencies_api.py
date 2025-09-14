import json


def create_framework(client, auth_headers, name='FW A'):
    resp = client.post('/api/frameworks', data=json.dumps({'name': name}), headers=auth_headers)
    assert resp.status_code == 201
    return resp.get_json()['framework']


def test_competency_crud(client, auth_headers):
    fw = create_framework(client, auth_headers, name='Framework X')

    # Create competency
    payload = {
        'name': 'Communication',
        'framework_id': fw['id'],
        'description': 'Clear communication'
    }
    resp = client.post('/api/competencies', data=json.dumps(payload), headers=auth_headers)
    assert resp.status_code == 201
    comp = resp.get_json()['competency']
    cid = comp['id']
    assert comp['framework_id'] == fw['id']

    # Get competency with metrics
    resp = client.get(f'/api/competencies/{cid}?include=metrics')
    assert resp.status_code == 200
    got = resp.get_json()['competency']
    assert got['id'] == cid

    # Update
    resp = client.patch(
        f'/api/competencies/{cid}',
        data=json.dumps({'name': 'Communication & Collaboration', 'sort_order': 2}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.get_json()['competency']
    assert updated['name'].startswith('Communication')
    assert updated['sort_order'] == 2

    # Delete
    resp = client.delete(f'/api/competencies/{cid}', headers=auth_headers)
    assert resp.status_code == 200


def test_competency_metric_associations(client, auth_headers, sample_metric_ids):
    fw = create_framework(client, auth_headers, name='Framework Assoc')
    # Create competency
    resp = client.post('/api/competencies', data=json.dumps({'name': 'Strategy', 'framework_id': fw['id']}), headers=auth_headers)
    assert resp.status_code == 201
    comp = resp.get_json()['competency']
    cid = comp['id']

    # Initially empty
    resp = client.get(f'/api/competencies/{cid}/metrics')
    assert resp.status_code == 200
    assert resp.get_json()['count'] == 0

    # Set metrics
    resp = client.put(
        f'/api/competencies/{cid}/metrics',
        data=json.dumps({'metric_ids': sample_metric_ids}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'competency' in data and 'metrics' in data['competency']
    assert len(data['competency']['metrics']) == len(sample_metric_ids)

    # Add one (idempotent add)
    resp = client.post(
        f'/api/competencies/{cid}/metrics/add',
        data=json.dumps({'metric_ids': [sample_metric_ids[0]]}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['competency']['metrics']) == len(sample_metric_ids)

    # Remove one
    resp = client.post(
        f'/api/competencies/{cid}/metrics/remove',
        data=json.dumps({'metric_ids': [sample_metric_ids[0]]}),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['competency']['metrics']) == len(sample_metric_ids) - 1
