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
    
    def store_context(self, context_type: str, data: Dict[str, Any], session_id: Optional[str] = None) -> bool:
        """Store context data in session."""
        try:
            if session_id is None:
                session_id = self.get_session_id()
            
            context_key = f'context_{context_type}'
            flask_session[context_key] = {
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_id': session_id
            }
            return True
        except Exception as e:
            logger.error(f"Error storing context: {e}")
            return False
    
    def get_context(self, context_type: str, context_key: str = 'current') -> Optional[Dict[str, Any]]:
        """Retrieve context data from session."""
        try:
            context_key = f'context_{context_type}_{context_key}'
            if context_key not in flask_session:
                return None
                
            context_data = flask_session[context_key]
            # Check if context is expired
            if 'expires_at' in context_data and datetime.fromisoformat(context_data['expires_at']) < datetime.now(timezone.utc):
                del flask_session[context_key]
                return None
                
            return context_data.get('data')
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None
            
    def get_or_create_session(self) -> Dict[str, Any]:
        """Get or create a new session."""
        session_id = self.get_session_id()
        now = datetime.now(timezone.utc)
        
        return {
            'id': session_id,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'user_agent': request.headers.get('User-Agent', '')
        }
        
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            'contexts_count': len([k for k in flask_session.keys() if k.startswith('context_')]),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'is_authenticated': 'user_id' in flask_session,
            'admin_user_id': flask_session.get('user_id')
        }
        
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences."""
        return flask_session.get('user_preferences', {})
        
    def get_selected_metrics(self) -> List[Dict[str, Any]]:
        """Get selected metrics for the current session."""
        return flask_session.get('selected_metrics', [])
        
    def store_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Store user preferences in session."""
        try:
            flask_session['user_preferences'] = preferences
            return True
        except Exception as e:
            logger.error(f"Error storing user preferences: {e}")
            return False
    
    def clear_context(self, context_type: Optional[str] = None, context_key: str = 'current') -> bool:
        """Clear context data.
        
        Args:
            context_type: The type of context to clear. If None, clears all contexts.
            context_key: The specific context key to clear. Defaults to 'current'.
            
        Returns:
            bool: True if context was cleared successfully, False otherwise.
        """
        try:
            if context_type:
                full_key = f'context_{context_type}_{context_key}'
                if full_key in flask_session:
                    del flask_session[full_key]
                    return True
                return False
            else:
                # Clear all contexts for the current session
                keys_to_remove = [k for k in flask_session.keys() if k.startswith('context_')]
                for key in keys_to_remove:
                    del flask_session[key]
                return True
        except Exception as e:
            logger.error(f"Error clearing context: {e}")
            return False
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions (simplified version)."""
        return [{
            'session_id': self.get_session_id(),
            'created_date': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'is_active': True
        }]


# Global instance
context_manager = ContextManager()
