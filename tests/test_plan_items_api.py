import json

def test_plan_items_list_initially_empty(client):
    rv = client.get('/api/context/plan/items')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert isinstance(data['items'], list)
    assert data['count'] == 0


def test_plan_items_add_and_list(client):
    body = {
        'kind': 'bias',
        'label': 'Status Quo Bias',
        'source_id': None,
        'meta': {'source': 'test'},
        'source_page': 'pytest'
    }
    rv = client.post('/api/context/plan/items', data=json.dumps(body), content_type='application/json')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    item = data['item']
    assert item['id'] == 1
    assert item['kind'] == 'bias'
    assert item['label'] == 'Status Quo Bias'
    assert item['meta'].get('source') == 'test'

    # List should include the new item
    rv2 = client.get('/api/context/plan/items')
    assert rv2.status_code == 200
    data2 = rv2.get_json()
    assert data2['count'] == 1
    assert data2['items'][0]['label'] == 'Status Quo Bias'


def test_plan_items_invalid_kind_returns_400(client):
    body = { 'kind': 'unknown', 'label': 'X' }
    rv = client.post('/api/context/plan/items', data=json.dumps(body), content_type='application/json')
    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'Invalid kind' in data['error']


def test_plan_items_remove_item_and_clear(client):
    # Add two items
    for payload in [
        { 'kind': 'driver', 'label': 'Coaching Conversations', 'source_id': 101 },
        { 'kind': 'bias', 'label': 'Framing Effect' },
    ]:
        rv = client.post('/api/context/plan/items', data=json.dumps(payload), content_type='application/json')
        assert rv.status_code == 200

    # Remove first by id
    rv_del = client.delete('/api/context/plan/items/1')
    assert rv_del.status_code == 200
    data_del = rv_del.get_json()
    assert data_del['success'] is True
    assert data_del['removed_id'] == 1

    # Verify only one remains
    rv_list = client.get('/api/context/plan/items')
    data_list = rv_list.get_json()
    assert data_list['count'] == 1
    assert data_list['items'][0]['label'] == 'Framing Effect'

    # Clear all
    rv_clear = client.delete('/api/context/plan/items')
    assert rv_clear.status_code == 200
    assert rv_clear.get_json()['success'] is True

    # Verify empty
    rv_list2 = client.get('/api/context/plan/items')
    data_list2 = rv_list2.get_json()
    assert data_list2['count'] == 0
