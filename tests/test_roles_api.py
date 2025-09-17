import json
import pytest

from app import db
from app.models import RoleProfile


def _create_role(client, auth_headers, name="QA Engineer"):
    resp = client.post('/api/roles', data=json.dumps({
        'name': name,
        'department': 'Engineering',
        'is_active': True
    }), headers=auth_headers)
    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    data = resp.get_json()
    assert 'role' in data
    return data['role']


def _create_framework_and_competency(client, auth_headers):
    # Create a framework
    fr = client.post('/api/frameworks', data=json.dumps({
        'name': 'QA Framework',
        'slug': 'qa-framework',
        'description': 'Test framework',
        'is_active': True,
        'is_builtin': True,
        'sort_order': 1
    }), headers=auth_headers)
    assert fr.status_code in (200, 201), fr.get_data(as_text=True)
    fw = fr.get_json()['framework']

    # Create a competency in that framework
    cr = client.post('/api/competencies', data=json.dumps({
        'name': 'Automation',
        'framework_id': fw['id'],
        'slug': 'automation',
        'description': 'Test competency'
    }), headers=auth_headers)
    assert cr.status_code in (200, 201), cr.get_data(as_text=True)
    comp = cr.get_json()['competency']
    return fw, comp


def test_roles_crud_flow(client, auth_headers):
    # Create
    role = _create_role(client, auth_headers, name="QA Engineer")
    role_id = role['id']

    # List
    res_list = client.get('/api/roles')
    assert res_list.status_code == 200
    data_list = res_list.get_json()
    assert any(r['id'] == role_id for r in data_list.get('roles', []))

    # Get single
    res_get = client.get(f'/api/roles/{role_id}')
    assert res_get.status_code == 200
    assert res_get.get_json()['role']['id'] == role_id

    # Update
    res_upd = client.patch(f'/api/roles/{role_id}', data=json.dumps({'name': 'QA Engineer II'}), headers=auth_headers)
    assert res_upd.status_code == 200
    assert res_upd.get_json()['role']['name'] == 'QA Engineer II'

    # Delete
    res_del = client.delete(f'/api/roles/{role_id}', headers=auth_headers)
    assert res_del.status_code == 200


def test_role_targets_flow(client, auth_headers):
    role = _create_role(client, auth_headers, name="QA Analyst")
    role_id = role['id']

    # Initially empty
    res_empty = client.get(f'/api/roles/{role_id}/targets')
    assert res_empty.status_code in (200, 404)
    if res_empty.status_code == 200:
        d = res_empty.get_json()
        assert 'targets' in d

    # Create a framework + competency and upsert targets
    fw, comp = _create_framework_and_competency(client, auth_headers)
    payload = {
        'targets': [
            {'competency_id': comp['id'], 'target_level': 3, 'weight': 1.0}
        ]
    }
    res_upsert = client.post(f'/api/roles/{role_id}/targets', data=json.dumps(payload), headers=auth_headers)
    assert res_upsert.status_code in (200, 201), res_upsert.get_data(as_text=True)

    # Fetch again
    res_after = client.get(f'/api/roles/{role_id}/targets')
    assert res_after.status_code == 200
    items = res_after.get_json().get('targets', [])
    assert any(t.get('competency_id') == comp['id'] for t in items)


def test_role_selection_session(client, auth_headers):
    # Initially none
    res0 = client.get('/api/roles/select')
    assert res0.status_code == 200
    assert res0.get_json().get('selected_role_profile_id') in (None, 0)

    # Create a role to select
    role = _create_role(client, auth_headers, name="Role To Select")
    # Set selection to the created role id
    res_set = client.post('/api/roles/select', data=json.dumps({'role_profile_id': role['id']}), headers=auth_headers)
    assert res_set.status_code == 200
    assert res_set.get_json()['selected_role_profile_id'] == role['id']

    # Get again
    res1 = client.get('/api/roles/select')
    assert res1.status_code == 200
    assert res1.get_json()['selected_role_profile_id'] == role['id']
