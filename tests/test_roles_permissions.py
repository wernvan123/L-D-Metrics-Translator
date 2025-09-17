import json

def test_roles_write_requires_admin(client):
    # Create should fail without admin headers
    resp = client.post('/api/roles', data=json.dumps({'name': 'NoAuth Role'}), headers={'Content-Type': 'application/json'})
    assert resp.status_code in (401, 403)

    # Update should fail
    resp = client.patch('/api/roles/1', data=json.dumps({'name': 'NoAuth Edit'}), headers={'Content-Type': 'application/json'})
    assert resp.status_code in (401, 403, 404)  # 404 acceptable if role doesn't exist

    # Delete should fail
    resp = client.delete('/api/roles/1')
    assert resp.status_code in (401, 403, 404)


def test_roles_read_is_public(client):
    resp = client.get('/api/roles')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'roles' in data
