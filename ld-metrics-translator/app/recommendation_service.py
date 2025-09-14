"""
Smart AI Recommendation Service with Context Integration

This service provides context-aware recommendations for L&D metrics based on:
- User preferences and behavior patterns
- Historical selections and feedback
- Current session context
- Similar user patterns (collaborative filtering)
- Content similarity (content-based filtering)
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import logging

from app import db
# Import models with optional advanced recommendation models (provide safe fallbacks if missing)
try:
    from app.models import (
        Metric, LDOutcome, MetricType, UserSession, UserContext,
        MetricSelection, UserPreference, Recommendation, RecommendationEngine,
        RecommendationFeedback, RecommendationHistory, Experience, EventAnalysis
    )
    HAVE_ADVANCED_MODELS = True
except ImportError:
    from app.models import (
        Metric, LDOutcome, MetricType,
        MetricSelection
    )
    # Try to import EventAnalysis optionally; if missing, define a stub
    try:
        from app.models import EventAnalysis
    except ImportError:
        class EventAnalysis:
            @staticmethod
            def get_recent_searches(limit=5):
                return []
    HAVE_ADVANCED_MODELS = False

    class UserPreference:  # Fallback stub to avoid hard dependency when model not present
        @staticmethod
        def get_preferences(session_id):
            return []

        @staticmethod
        def set_preference(session_id, preference_type, preference_key, preference_value, weight=1.0, admin_user_id=None):
            return None

    class Recommendation:  # Fallback with minimal to_dict support
        def __init__(self, **kwargs):
            self._data = kwargs
            self.confidence_score = kwargs.get('confidence_score', 0)
            self.viewed_at = None
            self.clicked_at = None
            self.dismissed_at = None
            self.accepted_at = None

        def to_dict(self):
            return {
                'id': None,
                'recommendation_type': self._data.get('recommendation_type'),
                'target_id': self._data.get('target_id'),
                'title': self._data.get('title'),
                'description': self._data.get('description'),
                'reasoning': self._data.get('reasoning'),
                'confidence_score': self._data.get('confidence_score', 0),
                'context_data': self._data.get('context_data', {}),
            }

    class RecommendationEngine:  # Fallback engine with default config
        def __init__(self, configuration):
            self.id = 0
            self.configuration = configuration

    class RecommendationFeedback:  # Fallback noop
        @staticmethod
        def add_feedback(**kwargs):
            return None

        @staticmethod
        def get_feedback_summary(rec_id):
            return {'total_feedback': 0, 'positive': 0, 'negative': 0, 'neutral': 0}

    class RecommendationHistory:  # Fallback noop
        @staticmethod
        def create_entry(**kwargs):
            return None

logger = logging.getLogger(__name__)


class SmartRecommendationService:
    """Context-aware recommendation service for L&D metrics."""
    
    def __init__(self):
        self.default_engine = self._get_or_create_default_engine()
    
    def _get_or_create_default_engine(self) -> RecommendationEngine:
        """Get or create the default recommendation engine."""
        config = {
            'weights': {
                'user_preferences': 0.3,
                'session_context': 0.25,
                'historical_selections': 0.2,
                'content_similarity': 0.15,
                'collaborative_filtering': 0.1
            },
            'min_confidence_threshold': 0.3,
            'max_recommendations': 10,
            'diversity_factor': 0.2
        }

        if HAVE_ADVANCED_MODELS:
            engine = RecommendationEngine.query.filter_by(name='default_context_aware').first()
            if not engine:
                engine = RecommendationEngine(
                    name='default_context_aware',
                    description='Default context-aware recommendation engine using multiple signals',
                    model_type='context_aware',
                    configuration=json.dumps(config)
                )
                db.session.add(engine)
                db.session.commit()
            return engine
        else:
            # Return simple in-memory engine when models are unavailable
            return RecommendationEngine(configuration=json.dumps(config))
    
    def generate_recommendations(
        self, 
        session_id: int, 
        context_data: Optional[Dict[str, Any]] = None,
        recommendation_type: str = 'metric',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate context-aware recommendations for a user session.
        
        Args:
            session_id: User session ID
            context_data: Additional context for recommendations
            recommendation_type: Type of recommendations ('metric', 'outcome', 'analysis')
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommendation dictionaries
        """
        start_time = time.time()
        
        try:
            # Get session and user context (skip if model unavailable)
            try:
                session = UserSession.query.get(session_id)  # type: ignore[name-defined]
            except NameError:
                session = None
            if HAVE_ADVANCED_MODELS and not session:
                logger.warning(f"Session {session_id} not found")
                return []
            
            # Gather context signals
            context_signals = self._gather_context_signals(session_id, context_data)
            
            # Generate recommendations based on type
            if recommendation_type == 'metric':
                recommendations = self._generate_metric_recommendations(
                    session_id, context_signals, limit
                )
            elif recommendation_type == 'outcome':
                recommendations = self._generate_outcome_recommendations(
                    session_id, context_signals, limit
                )
            elif recommendation_type == 'analysis':
                recommendations = self._generate_analysis_recommendations(
                    session_id, context_signals, limit
                )
            else:
                logger.warning(f"Unknown recommendation type: {recommendation_type}")
                return []
            
            # Store recommendations in database
            stored_recommendations = []
            for rec_data in recommendations:
                recommendation = self._store_recommendation(
                    session_id, rec_data, context_signals
                )
                stored_recommendations.append(recommendation.to_dict())
            
            # Record generation history
            generation_time = int((time.time() - start_time) * 1000)
            avg_confidence = sum(r['confidence_score'] for r in recommendations) / len(recommendations) if recommendations else 0
            
            RecommendationHistory.create_entry(
                session_id=session_id,
                engine_id=self.default_engine.id,
                generation_context=context_signals,
                recommendations_count=len(recommendations),
                average_confidence=avg_confidence,
                generation_time_ms=generation_time
            )
            
            logger.info(f"Generated {len(recommendations)} recommendations for session {session_id} in {generation_time}ms")
            return stored_recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def _gather_context_signals(self, session_id: int, additional_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Gather all available context signals for recommendation generation."""
        signals = {
            'session_id': session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'additional_context': additional_context or {}
        }
        
        # User preferences
        preferences = UserPreference.get_preferences(session_id)
        signals['user_preferences'] = {
            pref.preference_type: {
                'key': pref.preference_key,
                'value': json.loads(pref.preference_value) if pref.preference_value else None,
                'weight': pref.weight
            } for pref in preferences
        }
        
        # Current session context
        try:
            session = UserSession.query.get(session_id)  # type: ignore[name-defined]
        except NameError:
            session = None
        if session:
            try:
                contexts = session.contexts.all()
            except Exception:
                contexts = []
            signals['session_contexts'] = {
                ctx.context_type: {
                    'key': ctx.context_key,
                    'data': json.loads(ctx.context_data) if ctx.context_data else None
                } for ctx in contexts if not getattr(ctx, 'is_expired', lambda: False)()
            }
        
        # Historical metric selections
        selections = MetricSelection.get_active_for_session(session_id)
        signals['current_selections'] = [sel.metric_id for sel in selections]
        
        # Recent selections (last 30 days)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_selections = MetricSelection.query.filter(
            MetricSelection.session_id == session_id,
            MetricSelection.selected_at >= recent_cutoff
        ).all()
        signals['recent_selections'] = [sel.metric_id for sel in recent_selections]
        
        # Recent event analyses for context - be compatible with method signature
        try:
            recent_analyses = EventAnalysis.get_recent_searches(limit=5, session_id=session_id)  # type: ignore[arg-type]
        except TypeError:
            recent_analyses = EventAnalysis.get_recent_searches(limit=5)
        signals['recent_analyses'] = [
            {
                'description': analysis.event_description[:100],
                'success': analysis.success,
                'created_date': analysis.created_date.isoformat()
            } for analysis in recent_analyses
        ]
        
        return signals
    
    def _generate_metric_recommendations(
        self, 
        session_id: int, 
        context_signals: Dict[str, Any], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate metric recommendations based on context signals."""
        recommendations = []
        
        # Get all available metrics
        all_metrics = Metric.query.all()
        current_selections = set(context_signals.get('current_selections', []))
        
        # Score each metric
        metric_scores = {}
        for metric in all_metrics:
            if metric.id in current_selections:
                continue  # Skip already selected metrics
            
            score = self._calculate_metric_score(metric, context_signals)
            if score > 0.3:  # Minimum threshold
                metric_scores[metric.id] = {
                    'metric': metric,
                    'score': score,
                    'reasoning': self._generate_metric_reasoning(metric, context_signals, score)
                }
        
        # Sort by score and apply diversity
        sorted_metrics = sorted(metric_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Apply diversity to avoid recommending too many similar metrics
        diverse_metrics = self._apply_diversity_filter(sorted_metrics, limit)
        
        # Create recommendation objects
        for metric_id, data in diverse_metrics[:limit]:
            recommendations.append({
                'recommendation_type': 'metric',
                'target_id': metric_id,
                'title': f"Consider: {data['metric'].name}",
                'description': data['metric'].description[:200] + "..." if len(data['metric'].description) > 200 else data['metric'].description,
                'reasoning': data['reasoning'],
                'confidence_score': min(data['score'], 1.0),
                'metadata': {
                    'metric_name': data['metric'].name,
                    'outcome': data['metric'].outcome.name if data['metric'].outcome else None,
                    'metric_type': data['metric'].metric_type.name if data['metric'].metric_type else None
                }
            })
        
        return recommendations
    
    def _calculate_metric_score(self, metric: Metric, context_signals: Dict[str, Any]) -> float:
        """Calculate relevance score for a metric based on context signals."""
        score = 0.0
        config = json.loads(self.default_engine.configuration)
        weights = config.get('weights', {})
        
        # User preferences signal
        preferences = context_signals.get('user_preferences', {})
        if 'metric_type' in preferences and metric.metric_type:
            pref_value = preferences['metric_type'].get('value')
            if pref_value and metric.metric_type.name.lower() in str(pref_value).lower():
                score += weights.get('user_preferences', 0.3) * preferences['metric_type'].get('weight', 1.0)
        
        if 'outcome' in preferences and metric.outcome:
            pref_value = preferences['outcome'].get('value')
            if pref_value and metric.outcome.name.lower() in str(pref_value).lower():
                score += weights.get('user_preferences', 0.3) * preferences['outcome'].get('weight', 1.0)
        
        # Session context signal
        session_contexts = context_signals.get('session_contexts', {})
        if 'search' in session_contexts:
            search_data = session_contexts['search'].get('data', {})
            search_query = search_data.get('query', '').lower()
            if search_query:
                if search_query in metric.name.lower() or search_query in metric.description.lower():
                    score += weights.get('session_context', 0.25)
        
        # Historical selections signal
        recent_selections = context_signals.get('recent_selections', [])
        if recent_selections:
            # Find metrics with similar outcomes or types
            similar_metrics = Metric.query.filter(
                db.or_(
                    Metric.outcome_id == metric.outcome_id,
                    Metric.metric_type_id == metric.metric_type_id
                ),
                Metric.id.in_(recent_selections)
            ).count()
            
            if similar_metrics > 0:
                score += weights.get('historical_selections', 0.2) * (similar_metrics / len(recent_selections))
        
        # Content similarity signal (based on description keywords)
        recent_analyses = context_signals.get('recent_analyses', [])
        for analysis in recent_analyses:
            description = analysis.get('description', '').lower()
            metric_text = (metric.name + ' ' + metric.description).lower()
            
            # Simple keyword overlap scoring
            description_words = set(description.split())
            metric_words = set(metric_text.split())
            overlap = len(description_words.intersection(metric_words))
            
            if overlap > 0:
                score += weights.get('content_similarity', 0.15) * (overlap / max(len(description_words), 1))
        
        # Collaborative filtering signal (simplified)
        # Find sessions with similar selections and see what else they selected
        if recent_selections:
            similar_sessions = db.session.query(MetricSelection.session_id).filter(
                MetricSelection.metric_id.in_(recent_selections),
                MetricSelection.session_id != context_signals['session_id']
            ).distinct().limit(10).all()
            
            if similar_sessions:
                session_ids = [s[0] for s in similar_sessions]
                popular_in_similar = db.session.query(MetricSelection.metric_id).filter(
                    MetricSelection.session_id.in_(session_ids),
                    MetricSelection.metric_id == metric.id
                ).count()
                
                if popular_in_similar > 0:
                    score += weights.get('collaborative_filtering', 0.1) * (popular_in_similar / len(session_ids))
        
        return score
    
    def _generate_metric_reasoning(self, metric: Metric, context_signals: Dict[str, Any], score: float) -> str:
        """Generate human-readable reasoning for why a metric was recommended."""
        reasons = []
        
        # Check user preferences
        preferences = context_signals.get('user_preferences', {})
        if 'metric_type' in preferences and metric.metric_type:
            pref_value = preferences['metric_type'].get('value')
            if pref_value and metric.metric_type.name.lower() in str(pref_value).lower():
                reasons.append(f"matches your preference for {metric.metric_type.name} metrics")
        
        if 'outcome' in preferences and metric.outcome:
            pref_value = preferences['outcome'].get('value')
            if pref_value and metric.outcome.name.lower() in str(pref_value).lower():
                reasons.append(f"aligns with your focus on {metric.outcome.name}")
        
        # Check recent selections
        recent_selections = context_signals.get('recent_selections', [])
        if recent_selections:
            similar_metrics = Metric.query.filter(
                db.or_(
                    Metric.outcome_id == metric.outcome_id,
                    Metric.metric_type_id == metric.metric_type_id
                ),
                Metric.id.in_(recent_selections)
            ).count()
            
            if similar_metrics > 0:
                reasons.append(f"complements your recent {metric.outcome.name if metric.outcome else 'metric'} selections")
        
        # Check session context
        session_contexts = context_signals.get('session_contexts', {})
        if 'search' in session_contexts:
            search_data = session_contexts['search'].get('data', {})
            search_query = search_data.get('query', '').lower()
            if search_query and (search_query in metric.name.lower() or search_query in metric.description.lower()):
                reasons.append(f"relevant to your search for '{search_query}'")
        
        if not reasons:
            reasons.append(f"highly relevant based on your activity patterns")
        
        confidence_text = "high" if score > 0.7 else "medium" if score > 0.5 else "moderate"
        return f"Recommended with {confidence_text} confidence because it {', and '.join(reasons)}."
    
    def _apply_diversity_filter(self, sorted_metrics: List[Tuple], limit: int) -> List[Tuple]:
        """Apply diversity filtering to avoid too many similar recommendations."""
        if not sorted_metrics:
            return []
        
        diverse_metrics = []
        outcome_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for metric_id, data in sorted_metrics:
            metric = data['metric']
            
            # Check diversity constraints
            outcome_name = metric.outcome.name if metric.outcome else 'unknown'
            type_name = metric.metric_type.name if metric.metric_type else 'unknown'
            
            # Limit recommendations per outcome and type
            if outcome_counts[outcome_name] >= 3 or type_counts[type_name] >= 2:
                continue
            
            diverse_metrics.append((metric_id, data))
            outcome_counts[outcome_name] += 1
            type_counts[type_name] += 1
            
            if len(diverse_metrics) >= limit:
                break
        
        return diverse_metrics
    
    def _generate_outcome_recommendations(
        self, 
        session_id: int, 
        context_signals: Dict[str, Any], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate L&D outcome recommendations."""
        recommendations = []
        
        # Get outcomes not heavily represented in current selections
        current_selections = context_signals.get('current_selections', [])
        if current_selections:
            selected_metrics = Metric.query.filter(Metric.id.in_(current_selections)).all()
            selected_outcomes = [m.outcome_id for m in selected_metrics if m.outcome_id]
            outcome_counts = Counter(selected_outcomes)
        else:
            outcome_counts = Counter()
        
        # Find underrepresented outcomes
        all_outcomes = LDOutcome.query.all()
        for outcome in all_outcomes:
            current_count = outcome_counts.get(outcome.id, 0)
            total_metrics = outcome.metrics.count()
            
            if total_metrics > 0 and current_count < max(1, total_metrics // 3):
                confidence = min(0.8, (total_metrics - current_count) / total_metrics)
                
                recommendations.append({
                    'recommendation_type': 'outcome',
                    'target_id': outcome.id,
                    'title': f"Explore {outcome.name} Metrics",
                    'description': outcome.description or f"Consider adding metrics focused on {outcome.name}",
                    'reasoning': f"You have {current_count} out of {total_metrics} available {outcome.name} metrics. Adding more could provide better coverage.",
                    'confidence_score': confidence,
                    'metadata': {
                        'outcome_name': outcome.name,
                        'current_count': current_count,
                        'total_available': total_metrics
                    }
                })
        
        # Sort by confidence and return top recommendations
        recommendations.sort(key=lambda x: x['confidence_score'], reverse=True)
        return recommendations[:limit]
    
    def _generate_analysis_recommendations(
        self, 
        session_id: int, 
        context_signals: Dict[str, Any], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate analysis and insight recommendations."""
        recommendations = []
        
        current_selections = context_signals.get('current_selections', [])
        if len(current_selections) < 2:
            return recommendations
        
        # Recommend correlation analysis
        if len(current_selections) >= 3:
            recommendations.append({
                'recommendation_type': 'analysis',
                'target_id': None,
                'title': "Correlation Analysis",
                'description': "Analyze relationships between your selected metrics to identify patterns and dependencies.",
                'reasoning': f"With {len(current_selections)} metrics selected, correlation analysis can reveal valuable insights about how these metrics influence each other.",
                'confidence_score': 0.8,
                'metadata': {
                    'analysis_type': 'correlation',
                    'metric_count': len(current_selections)
                }
            })
        
        # Recommend trend analysis
        recommendations.append({
            'recommendation_type': 'analysis',
            'target_id': None,
            'title': "Trend Analysis",
            'description': "Track how your selected metrics change over time to identify patterns and predict future performance.",
            'reasoning': "Time-series analysis of your metrics can help identify seasonal patterns, trends, and optimal measurement intervals.",
            'confidence_score': 0.7,
            'metadata': {
                'analysis_type': 'trend',
                'metric_count': len(current_selections)
            }
        })
        
        # Recommend benchmarking
        recommendations.append({
            'recommendation_type': 'analysis',
            'target_id': None,
            'title': "Industry Benchmarking",
            'description': "Compare your metrics against industry standards and best practices.",
            'reasoning': "Benchmarking helps contextualize your metrics and identify areas for improvement relative to industry peers.",
            'confidence_score': 0.6,
            'metadata': {
                'analysis_type': 'benchmark',
                'metric_count': len(current_selections)
            }
        })
        
        return recommendations[:limit]
    
    def _store_recommendation(
        self, 
        session_id: int, 
        rec_data: Dict[str, Any], 
        context_signals: Dict[str, Any]
    ) -> Recommendation:
        """Store a recommendation in the database."""
        if HAVE_ADVANCED_MODELS:
            recommendation = Recommendation(
                session_id=session_id,
                engine_id=self.default_engine.id,
                recommendation_type=rec_data['recommendation_type'],
                target_id=rec_data.get('target_id'),
                title=rec_data['title'],
                description=rec_data.get('description'),
                reasoning=rec_data.get('reasoning'),
                confidence_score=rec_data['confidence_score'],
                context_data=json.dumps({
                    'generation_context': context_signals,
                    'metadata': rec_data.get('metadata', {})
                })
            )
            db.session.add(recommendation)
            db.session.commit()
            return recommendation
        else:
            # Return a lightweight in-memory object
            return Recommendation(
                recommendation_type=rec_data['recommendation_type'],
                target_id=rec_data.get('target_id'),
                title=rec_data['title'],
                description=rec_data.get('description'),
                reasoning=rec_data.get('reasoning'),
                confidence_score=rec_data['confidence_score'],
                context_data={
                    'generation_context': context_signals,
                    'metadata': rec_data.get('metadata', {})
                }
            )
    
    def record_user_interaction(
        self, 
        recommendation_id: int, 
        interaction_type: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record user interaction with a recommendation."""
        if not HAVE_ADVANCED_MODELS:
            # No-op when models are unavailable
            return True
        try:
            recommendation = Recommendation.query.get(recommendation_id)
            if not recommendation:
                logger.warning(f"Recommendation {recommendation_id} not found")
                return False
            
            if interaction_type == 'viewed':
                recommendation.mark_viewed()
            elif interaction_type == 'clicked':
                recommendation.mark_clicked()
            elif interaction_type == 'dismissed':
                recommendation.mark_dismissed()
            elif interaction_type == 'accepted':
                recommendation.mark_accepted()
            else:
                logger.warning(f"Unknown interaction type: {interaction_type}")
                return False
            
            logger.info(f"Recorded {interaction_type} interaction for recommendation {recommendation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording interaction: {str(e)}")
            return False
    
    def add_feedback(
        self, 
        recommendation_id: int, 
        feedback_type: str,
        feedback_value: Optional[str] = None,
        feedback_text: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[RecommendationFeedback]:
        """Add user feedback for a recommendation."""
        if not HAVE_ADVANCED_MODELS:
            return None
        try:
            feedback = RecommendationFeedback.add_feedback(
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                feedback_value=feedback_value,
                feedback_text=feedback_text,
                ip_address=ip_address
            )
            
            logger.info(f"Added {feedback_type} feedback for recommendation {recommendation_id}")
            return feedback
            
        except Exception as e:
            logger.error(f"Error adding feedback: {str(e)}")
            return None
    
    def update_user_preferences(
        self, 
        session_id: int, 
        preferences: Dict[str, Any],
        admin_user_id: Optional[int] = None
    ) -> bool:
        """Update user preferences based on behavior and explicit feedback."""
        try:
            for pref_type, pref_data in preferences.items():
                if isinstance(pref_data, dict) and 'key' in pref_data and 'value' in pref_data:
                    UserPreference.set_preference(
                        session_id=session_id,
                        preference_type=pref_type,
                        preference_key=pref_data['key'],
                        preference_value=pref_data['value'],
                        weight=pref_data.get('weight', 1.0),
                        admin_user_id=admin_user_id
                    )
            
            logger.info(f"Updated preferences for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            return False
    
    def get_recommendation_analytics(self, session_id: int) -> Dict[str, Any]:
        """Get analytics for recommendations in a session."""
        if not HAVE_ADVANCED_MODELS:
            return {'total': 0, 'analytics': {}}
        try:
            recommendations = Recommendation.query.filter_by(session_id=session_id).all()
            
            if not recommendations:
                return {'total': 0, 'analytics': {}}
            
            analytics = {
                'total': len(recommendations),
                'by_type': defaultdict(int),
                'interactions': {
                    'viewed': 0,
                    'clicked': 0,
                    'dismissed': 0,
                    'accepted': 0
                },
                'average_confidence': 0,
                'feedback_summary': {
                    'total_feedback': 0,
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                }
            }
            
            total_confidence = 0
            for rec in recommendations:
                analytics['by_type'][rec.recommendation_type] += 1
                total_confidence += rec.confidence_score or 0
                
                if rec.viewed_at:
                    analytics['interactions']['viewed'] += 1
                if rec.clicked_at:
                    analytics['interactions']['clicked'] += 1
                if rec.dismissed_at:
                    analytics['interactions']['dismissed'] += 1
                if rec.accepted_at:
                    analytics['interactions']['accepted'] += 1
                
                # Aggregate feedback
                feedback_summary = RecommendationFeedback.get_feedback_summary(rec.id)
                analytics['feedback_summary']['total_feedback'] += feedback_summary['total_feedback']
                analytics['feedback_summary']['positive'] += feedback_summary['positive']
                analytics['feedback_summary']['negative'] += feedback_summary['negative']
                analytics['feedback_summary']['neutral'] += feedback_summary['neutral']
            
            analytics['average_confidence'] = total_confidence / len(recommendations)
            analytics['by_type'] = dict(analytics['by_type'])
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {'total': 0, 'analytics': {}, 'error': str(e)}


# Global service instance
recommendation_service = SmartRecommendationService()
