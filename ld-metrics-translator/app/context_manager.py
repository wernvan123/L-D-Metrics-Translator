"""
Simple Context Manager for L&D Metrics Translator
Minimal implementation without complex database relationships.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from flask import request, session as flask_session
from app import db
from app.models import Metric
import logging

logger = logging.getLogger(__name__)


class ContextManager:
    """Simplified context management system."""
    
    def __init__(self):
        """Initialize the context manager."""
        self.session_timeout = timedelta(hours=24)
    
    def get_session_id(self) -> str:
        """Get or create session ID."""
        if 'session_id' not in flask_session:
            flask_session['session_id'] = str(uuid.uuid4())
        return flask_session['session_id']
    
    def store_context(self, context_type: str, context_key: str, context_data: Dict[str, Any], expires_in: Optional[timedelta] = None):
        """Store context data with type and key and return an object with to_dict()."""
        try:
            full_key = f'context_{context_type}_{context_key}'
            now = datetime.now(timezone.utc)
            expires_at = (now + expires_in) if expires_in else None
            flask_session[full_key] = {
                'data': context_data,
                'timestamp': now.isoformat(),
                'session_id': self.get_session_id(),
                'expires_at': expires_at.isoformat() if expires_at else None,
                'context_type': context_type,
                'context_key': context_key,
            }

            class StoredContext:
                def __init__(self, payload: Dict[str, Any]):
                    self.payload = payload
                def to_dict(self) -> Dict[str, Any]:
                    return {
                        'context_type': self.payload.get('context_type'),
                        'context_key': self.payload.get('context_key'),
                        'context_data': self.payload.get('data'),
                        'timestamp': self.payload.get('timestamp'),
                        'session_id': self.payload.get('session_id'),
                        'expires_at': self.payload.get('expires_at'),
                    }

            return StoredContext(flask_session[full_key])
        except Exception as e:
            logger.error(f"Error storing context {context_type}/{context_key}: {e}")
            raise
    
    def get_context(self, context_type: str, context_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve context data for specific type and key from session."""
        try:
            full_key = f'context_{context_type}_{context_key}'
            payload = flask_session.get(full_key)
            if not payload:
                return None
            return payload.get('data')
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return None
    
    def clear_context(self, context_type: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """Clear context data."""
        try:
            if context_type:
                context_key = f'context_{context_type}'
                if context_key in flask_session:
                    del flask_session[context_key]
            else:
                # Clear all context
                keys_to_remove = [k for k in flask_session.keys() if k.startswith('context_')]
                for key in keys_to_remove:
                    del flask_session[key]
            return True
        except Exception as e:
            logger.error(f"Error clearing context: {e}")
            return False
    
    def get_or_create_session(self, session_id: Optional[str] = None):
        """Get or create session (simplified version) and return an object with to_dict()."""
        if session_id is None:
            session_id = self.get_session_id()

        now = datetime.now(timezone.utc).isoformat()
        session_payload = {
            'session_id': session_id,
            'created_date': now,
            'last_activity': now,
            'is_active': True,
        }

        class SessionInfo:
            def __init__(self, payload: Dict[str, Any]):
                self.payload = payload
            def to_dict(self) -> Dict[str, Any]:
                return dict(self.payload)

        return SessionInfo(session_payload)
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions (simplified version)."""
        return [{
            'session_id': self.get_session_id(),
            'created_date': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'is_active': True
        }]
    
    def store_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Store user preferences."""
        try:
            flask_session['user_preferences'] = {
                'data': preferences,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_id': self.get_session_id()
            }
            return True
        except Exception as e:
            logger.error(f"Error storing user preferences: {e}")
            return False
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            if 'user_preferences' in flask_session:
                return flask_session['user_preferences'].get('data', {})
            return {}
        except (RuntimeError, Exception) as e:
            logger.error(f"Error retrieving user preferences: {e}")
            return {}
    
    def get_selected_metrics(self) -> List[Dict[str, Any]]:
        """Get selected metrics."""
        try:
            if 'context_metrics_selected' in flask_session:
                return flask_session['context_metrics_selected'].get('data', [])
            return []
        except (RuntimeError, Exception) as e:
            logger.error(f"Error retrieving selected metrics: {e}")
            return []

    # ---------------------------------------------
    # Framework-centric context helpers
    # ---------------------------------------------
    def set_selected_framework(self, framework_id: int):
        """Store currently selected framework for this session and return to_dict()."""
        try:
            payload = {
                'framework_id': int(framework_id),
                'selected_at': datetime.now(timezone.utc).isoformat(),
            }
            stored = self.store_context('framework', 'selected', payload)
            return stored.to_dict()
        except Exception as e:
            logger.error(f"Error setting selected framework: {e}")
            raise

    def get_selected_framework(self) -> Optional[Dict[str, Any]]:
        """Return selected framework context or None."""
        try:
            return self.get_context('framework', 'selected')
        except Exception as e:
            logger.error(f"Error getting selected framework: {e}")
            return None

    def set_active_competencies(self, competency_ids: List[int]):
        """Store active competency IDs for the current framework selection."""
        try:
            payload = {
                'competency_ids': [int(x) for x in (competency_ids or [])],
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            stored = self.store_context('framework', 'active_competencies', payload)
            return stored.to_dict()
        except Exception as e:
            logger.error(f"Error setting active competencies: {e}")
            raise

    def get_active_competencies(self) -> List[int]:
        """Return list of active competency IDs, empty list if none."""
        try:
            data = self.get_context('framework', 'active_competencies') or {}
            return list(data.get('competency_ids') or [])
        except Exception as e:
            logger.error(f"Error getting active competencies: {e}")
            return []

    def select_metric(self, metric_id: int, selection_type: str = 'manual', context_tags: Optional[List[str]] = None):
        """Toggle a metric selection for the session and return (selected: bool, selection_obj)."""
        from types import SimpleNamespace
        with_data = flask_session.get('context_metrics_selected') or {'data': []}
        selections: List[Dict[str, Any]] = with_data.get('data', [])

        # Validate metric
        metric = Metric.query.get(metric_id)
        if not metric:
            raise ValueError(f"Metric {metric_id} not found")

        # Check if already selected and active
        now_iso = datetime.now(timezone.utc).isoformat()
        for sel in selections:
            if sel.get('metric_id') == metric_id and sel.get('is_active', True):
                # Deselect
                sel['is_active'] = False
                sel['deselected_at'] = now_iso
                flask_session['context_metrics_selected'] = {'data': selections}

                def _to_dict(d):
                    return dict(d)
                return False, SimpleNamespace(to_dict=lambda d=sel: _to_dict(d))

        # Create new selection
        selection = {
            'id': len(selections) + 1,
            'session_id': self.get_session_id(),
            'metric_id': metric_id,
            'metric_name': metric.name,
            'selection_type': selection_type,
            'selected_at': now_iso,
            'deselected_at': None,
            'is_active': True,
            'context_tags': context_tags or [],
        }
        selections.append(selection)
        flask_session['context_metrics_selected'] = {'data': selections}

        def _to_dict(d):
            return dict(d)
        from types import SimpleNamespace
        return True, SimpleNamespace(to_dict=lambda d=selection: _to_dict(d))
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        try:
            return {
                'contexts_count': len([k for k in flask_session.keys() if k.startswith('context_')]),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'is_authenticated': 'user_id' in flask_session,
                'admin_user_id': flask_session.get('user_id')
            }
        except RuntimeError:
            # Outside request context
            return {
                'contexts_count': 0,
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'is_authenticated': False,
                'admin_user_id': None
            }

    # ---------------------------------------------
    # Plan Items (session-backed)
    # ---------------------------------------------
    def _ensure_plan_items(self) -> List[Dict[str, Any]]:
        """Internal helper to ensure plan items structure exists in session."""
        with_data = flask_session.get('context_plan_items') or {'data': []}
        if 'data' not in with_data or not isinstance(with_data['data'], list):
            with_data = {'data': []}
        flask_session['context_plan_items'] = with_data
        return with_data['data']

    def list_plan_items(self) -> List[Dict[str, Any]]:
        """Return the current plan items list for the session."""
        try:
            items = self._ensure_plan_items()
            # Return a shallow copy to avoid accidental mutation
            return [dict(x) for x in items]
        except Exception as e:
            logger.error(f"Error listing plan items: {e}")
            return []

    def add_plan_item(self, kind: str, label: str, source_id: Optional[Any] = None, meta: Optional[Dict[str, Any]] = None, source_page: Optional[str] = None) -> Dict[str, Any]:
        """Add an item to the plan for this session and return the stored dict."""
        try:
            if not kind or not label:
                raise ValueError("kind and label are required")
            kind_l = str(kind).lower()
            allowed = {"driver", "bias", "metric", "outcome", "competency", "kpi", "nudge", "gap"}
            if kind_l not in allowed:
                raise ValueError(f"Invalid kind '{kind}'. Must be one of {sorted(allowed)}")

            items = self._ensure_plan_items()
            now_iso = datetime.now(timezone.utc).isoformat()
            new_id = (items[-1]['id'] + 1) if items else 1
            item = {
                'id': int(new_id),
                'session_id': self.get_session_id(),
                'kind': kind_l,
                'label': str(label),
                'source_id': source_id,
                'meta': meta or {},
                'source_page': source_page or '',
                'added_at': now_iso,
            }
            items.append(item)
            flask_session['context_plan_items'] = {'data': items}
            return dict(item)
        except Exception as e:
            logger.error(f"Error adding plan item: {e}")
            raise

    def remove_plan_item(self, item_id: int) -> bool:
        """Remove an item by id from the session plan items."""
        try:
            items = self._ensure_plan_items()
            idx = next((i for i, it in enumerate(items) if it.get('id') == int(item_id)), None)
            if idx is None:
                return False
            items.pop(idx)
            flask_session['context_plan_items'] = {'data': items}
            return True
        except Exception as e:
            logger.error(f"Error removing plan item {item_id}: {e}")
            return False

    def clear_plan_items(self) -> bool:
        """Clear all plan items for the session."""
        try:
            flask_session['context_plan_items'] = {'data': []}
            return True
        except Exception as e:
            logger.error(f"Error clearing plan items: {e}")
            return False


# Global instance
context_manager = ContextManager()
