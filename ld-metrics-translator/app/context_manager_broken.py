"""
Context Manager for L&D Metrics Translator
Handles user sessions, context storage, and metric selections.
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
    """Core context management system for user sessions and data persistence."""
    
    def __init__(self):
        """Initialize the context manager."""
        self.default_context_expiry = timedelta(hours=24)
        self.session_timeout = timedelta(hours=2)
    
    def get_session_id(self) -> str:
        """Get or create a session ID for the current request."""
        # Try to get session ID from Flask session first
        if 'session_id' in flask_session:
            return flask_session['session_id']
        
        # Try to get from request headers
        session_id = request.headers.get('X-Session-ID')
        if session_id:
            flask_session['session_id'] = session_id
            return session_id
        
        # Generate new session ID
        session_id = str(uuid.uuid4())
        flask_session['session_id'] = session_id
        flask_session.permanent = True
        
        return session_id
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> UserSession:
        """Get existing session or create a new one."""
        if not session_id:
            session_id = self.get_session_id()
        
        # Extract request metadata
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', '')
        
        # Check if user is authenticated
        admin_user_id = flask_session.get('admin_user_id')
        if admin_user_id:
            user_identifier = f"admin_{admin_user_id}"
        else:
            user_identifier = ip_address  # For anonymous users, use IP as identifier
        
        try:
            session = UserSession.get_or_create(
                session_id=session_id,
                user_identifier=user_identifier,
                user_agent=user_agent,
                ip_address=ip_address
            )
            return session
        except Exception as e:
            logger.error(f"Error creating/retrieving session: {str(e)}")
            raise
    
    def store_context(self, context_type: str, context_key: str, 
                     context_data: Dict[str, Any], session_id: Optional[str] = None,
                     expires_in: Optional[timedelta] = None) -> UserContext:
        """Store context data for a user session."""
        session = self.get_or_create_session(session_id)
        
        # Calculate expiration time
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + expires_in
        elif self.default_context_expiry:
            expires_at = datetime.now(timezone.utc) + self.default_context_expiry
        
        try:
            # Check if context already exists
            existing_context = UserContext.query.filter_by(
                session_id=session.id,
                context_type=context_type,
                context_key=context_key
            ).first()
            
            if existing_context:
                # Update existing context
                existing_context.context_data = json.dumps(context_data)
                existing_context.updated_date = datetime.now(timezone.utc)
                existing_context.expires_at = expires_at
                db.session.commit()
                return existing_context
            else:
                # Create new context
                new_context = UserContext(
                    session_id=session.id,
                    context_type=context_type,
                    context_key=context_key,
                    context_data=json.dumps(context_data),
                    expires_at=expires_at
                )
                db.session.add(new_context)
                db.session.commit()
                return new_context
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing context: {str(e)}")
            raise
    
    def get_context(self, context_type: str, context_key: str, 
                   session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve context data for a user session."""
        session = self.get_or_create_session(session_id)
        
        try:
            context = UserContext.query.filter_by(
                session_id=session.id,
                context_type=context_type,
                context_key=context_key
            ).first()
            
            if not context:
                return None
            
            # Check if context has expired
            if context.is_expired():
                # Delete expired context
                db.session.delete(context)
                db.session.commit()
                return None
            
            # Update session activity
            session.update_activity()
            
            # Parse JSON data
            return json.loads(context.context_data)
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error retrieving context {context_type}:{context_key}: {str(e)}")
            return None
                
    def get_all_contexts(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all contexts for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            contexts = UserContext.query.filter_by(session_id=session.id).all()
            result = []
            
            for context in contexts:
                if not context.is_expired():
                    result.append(context.to_dict())
                else:
                    # Clean up expired context
                    db.session.delete(context)
            
            db.session.commit()
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving all contexts: {str(e)}")
            return []
    
    def delete_context(self, context_type: str, context_key: str, 
                      session_id: Optional[str] = None) -> bool:
        """Delete specific context data."""
        session = self.get_or_create_session(session_id)
        
        try:
            context = UserContext.query.filter_by(
                session_id=session.id,
                context_type=context_type,
                context_key=context_key
            ).first()
            
            if context:
                db.session.delete(context)
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting context: {str(e)}")
            return False
    
    def clear_session_contexts(self, session_id: Optional[str] = None) -> bool:
        """Clear all contexts for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            UserContext.query.filter_by(session_id=session.id).delete()
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing session contexts: {str(e)}")
            return False
    
    def store_search_context(self, search_query: str, filters: Dict[str, Any], 
                           results_count: int, session_id: Optional[str] = None) -> UserContext:
        """Store search context for later reference."""
        context_data = {
            'query': search_query,
            'filters': filters,
            'results_count': results_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return self.store_context(
            context_type='search',
            context_key='last_search',
            context_data=context_data,
            session_id=session_id
        )
    
    def get_search_history(self, limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent search history for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            contexts = UserContext.query.filter_by(
                session_id=session.id,
                context_type='search'
            ).order_by(UserContext.updated_date.desc()).limit(limit).all()
            
            history = []
            for context in contexts:
                if not context.is_expired():
                    try:
                        data = json.loads(context.context_data)
                        history.append({
                            'key': context.context_key,
                            'query': data.get('query', ''),
                            'filters': data.get('filters', {}),
                            'results_count': data.get('results_count', 0),
                            'timestamp': data.get('timestamp', context.updated_date.isoformat())
                        })
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            return history
            
        except Exception as e:
            logger.error(f"Error retrieving search history: {str(e)}")
            return []
    
    def store_user_preferences(self, preferences: Dict[str, Any], 
                             session_id: Optional[str] = None) -> UserContext:
        """Store user preferences."""
        return self.store_context(
            context_type='preferences',
            context_key='user_prefs',
            context_data=preferences,
            session_id=session_id,
            expires_in=timedelta(days=30)  # Longer expiry for preferences
        )
    
    def get_user_preferences(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user preferences with defaults."""
        preferences = self.get_context('preferences', 'user_prefs', session_id)
        
        # Default preferences
        defaults = {
            'theme': 'light',
            'results_per_page': 20,
            'auto_save_selections': True,
            'show_advanced_filters': False,
            'preferred_metric_types': [],
            'preferred_outcomes': []
        }
        
        # Return defaults if no preferences found
        if not preferences:
            return defaults
        
        # Merge with defaults to ensure all keys exist
        merged_prefs = defaults.copy()
        merged_prefs.update(preferences)
        return merged_prefs
    
    def select_metric(self, metric_id: int, selection_type: str = 'manual',
                     context_tags: Optional[List[str]] = None, 
                     session_id: Optional[str] = None) -> Tuple[bool, MetricSelection]:
        """Select a metric for the current session."""
        session = self.get_or_create_session(session_id)
        
        try:
            # Verify metric exists
            metric = Metric.query.get(metric_id)
            if not metric:
                raise ValueError(f"Metric with ID {metric_id} not found")
            
            selected, selection = MetricSelection.toggle_selection(
                session_id=session.id,
                metric_id=metric_id,
                selection_type=selection_type,
                context_tags=context_tags
            )
            
            # Update context with current selections
            self._update_selection_context(session.id)
            
            return selected, selection
            
        except Exception as e:
            logger.error(f"Error selecting metric: {str(e)}")
            raise
    
    def get_selected_metrics(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all selected metrics for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            selections = MetricSelection.get_active_for_session(session.id)
            return [selection.to_dict() for selection in selections]
            
        except Exception as e:
            logger.error(f"Error retrieving selected metrics: {str(e)}")
            return []
    
    def clear_metric_selections(self, session_id: Optional[str] = None) -> bool:
        """Clear all metric selections for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            selections = MetricSelection.get_active_for_session(session.id)
            for selection in selections:
                selection.deselect()
            
            # Update context
            self._update_selection_context(session.id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing metric selections: {str(e)}")
            return False
    
    def _update_selection_context(self, session_id: int) -> None:
        """Update the selection context with current metric selections."""
        try:
            selections = MetricSelection.get_active_for_session(session_id)
            selection_data = {
                'metric_ids': [s.metric_id for s in selections],
                'count': len(selections),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'selection_types': {s.metric_id: s.selection_type for s in selections}
            }
            
            # Store in context
            context = UserContext.query.filter_by(
                session_id=session_id,
                context_type='selections',
                context_key='current_metrics'
            ).first()
            
            if context:
                context.context_data = json.dumps(selection_data)
                context.updated_date = datetime.now(timezone.utc)
            else:
                context = UserContext(
                    session_id=session_id,
                    context_type='selections',
                    context_key='current_metrics',
                    context_data=json.dumps(selection_data)
                )
                db.session.add(context)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating selection context: {str(e)}")
            db.session.rollback()
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and their contexts."""
        try:
            cutoff_time = datetime.now(timezone.utc) - self.session_timeout
            
            # Find expired sessions
            expired_sessions = UserSession.query.filter(
                UserSession.last_activity < cutoff_time
            ).all()
            
            count = 0
            for session in expired_sessions:
                # Delete associated contexts and selections
                UserContext.query.filter_by(session_id=session.id).delete()
                MetricSelection.query.filter_by(session_id=session.id).delete()
                db.session.delete(session)
                count += 1
            
            db.session.commit()
            logger.info(f"Cleaned up {count} expired sessions")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
    
    def get_session_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a session."""
        session = self.get_or_create_session(session_id)
        
        try:
            contexts_count = UserContext.query.filter_by(session_id=session.id).count()
            selections_count = MetricSelection.query.filter_by(
                session_id=session.id, is_active=True
            ).count()
            
            # Check authentication status
            admin_user_id = flask_session.get('admin_user_id')
            is_authenticated = admin_user_id is not None
            
            return {
                'session_id': session.session_id,
                'created_date': session.created_date.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'contexts_count': contexts_count,
                'active_selections_count': selections_count,
                'is_active': session.is_active,
                'is_authenticated': is_authenticated,
                'admin_user_id': admin_user_id
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session stats: {str(e)}")
            return {}
    
    def store_event_analysis(self, event_description: str, analysis_result: str, 
                           generated_by: str = 'ai_model', success: bool = True, 
                           error_message: str = None, session_id: Optional[str] = None) -> 'EventAnalysis':
        """Store event analysis with authentication awareness."""
        from app.models import EventAnalysis
        
        session = self.get_or_create_session(session_id)
        admin_user_id = flask_session.get('admin_user_id')
        
        try:
            analysis = EventAnalysis(
                event_description=event_description,
                analysis_result=analysis_result,
                generated_by=generated_by,
                success=success,
                error_message=error_message,
                session_id=session.id,
                admin_user_id=admin_user_id,
                is_anonymous=admin_user_id is None,
                ip_address=request.remote_addr
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            return analysis
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing event analysis: {str(e)}")
            raise
    
    def get_event_analysis_history(self, limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get event analysis history based on authentication status."""
        from app.models import EventAnalysis
        
        admin_user_id = flask_session.get('admin_user_id')
        
        try:
            if admin_user_id:
                # Authenticated user - get their personal history
                analyses = EventAnalysis.get_user_history(admin_user_id, limit)
            else:
                # Anonymous user - get session-specific history
                session = self.get_or_create_session(session_id)
                analyses = EventAnalysis.get_session_history(session.id, limit)
            
            return [analysis.to_dict() for analysis in analyses]
            
        except Exception as e:
            logger.error(f"Error retrieving event analysis history: {str(e)}")
            return []
    
    def clear_event_analysis_history(self, session_id: Optional[str] = None) -> bool:
        """Clear event analysis history based on authentication status."""
        from app.models import EventAnalysis
        
        admin_user_id = flask_session.get('admin_user_id')
        
        try:
            if admin_user_id:
                # Authenticated user - clear their personal history
                return EventAnalysis.clear_user_history(admin_user_id)
            else:
                # Anonymous user - clear session-specific history
                session = self.get_or_create_session(session_id)
                return EventAnalysis.clear_session_history(session.id)
                
        except Exception as e:
            logger.error(f"Error clearing event analysis history: {str(e)}")
            return False


# Global instance
context_manager = ContextManager()
