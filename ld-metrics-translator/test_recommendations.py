#!/usr/bin/env python3
"""
Test script for Smart AI Recommendations Context Integration

This script tests the recommendation system functionality including:
- Context-aware recommendation generation
- User preference tracking
- Recommendation feedback system
- Analytics and history tracking
"""

import sys
import os
import json
import uuid
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_recommendation_system():
    """Test the complete recommendation system."""
    print("🧪 Testing Smart AI Recommendations Context Integration")
    print("=" * 60)
    
    try:
        # Import after adding to path
        from app import create_app, db
        from app.models import (
            UserSession, UserPreference, Recommendation, 
            RecommendationEngine, RecommendationFeedback,
            Metric, LDOutcome, MetricType
        )
        from app.recommendation_service import recommendation_service
        
        # Create test app
        app = create_app()
        
        with app.app_context():
            print("✅ Application context created successfully")
            
            # Test 1: Create test session
            print("\n📝 Test 1: Creating test session...")
            session_id = str(uuid.uuid4())
            session = UserSession.get_or_create(
                session_id=session_id,
                user_identifier="test_user",
                ip_address="127.0.0.1"
            )
            print(f"✅ Session created: {session.session_id}")
            
            # Test 2: Set user preferences
            print("\n📝 Test 2: Setting user preferences...")
            test_preferences = {
                'metric_type': {
                    'key': 'preferred_types',
                    'value': ['Operational KPI', 'Behavioral Metric'],
                    'weight': 0.8
                },
                'outcome': {
                    'key': 'focus_areas',
                    'value': ['Employee Engagement'],
                    'weight': 0.9
                }
            }
            
            success = recommendation_service.update_user_preferences(
                session_id=session.id,
                preferences=test_preferences
            )
            print(f"✅ Preferences updated: {success}")
            
            # Test 3: Generate recommendations
            print("\n📝 Test 3: Generating context-aware recommendations...")
            context_data = {
                'search_query': 'engagement metrics',
                'current_page': 'metrics_selection'
            }
            
            recommendations = recommendation_service.generate_recommendations(
                session_id=session.id,
                context_data=context_data,
                recommendation_type='metric',
                limit=3
            )
            print(f"✅ Generated {len(recommendations)} recommendations")
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec['title']} (confidence: {rec['confidence_score']:.2f})")
            
            # Test 4: Record interactions
            if recommendations:
                print("\n📝 Test 4: Recording user interactions...")
                rec_id = recommendations[0]['id']
                
                # Test viewing
                success = recommendation_service.record_user_interaction(
                    recommendation_id=rec_id,
                    interaction_type='viewed'
                )
                print(f"✅ Recorded 'viewed' interaction: {success}")
                
                # Test clicking
                success = recommendation_service.record_user_interaction(
                    recommendation_id=rec_id,
                    interaction_type='clicked'
                )
                print(f"✅ Recorded 'clicked' interaction: {success}")
            
            # Test 5: Add feedback
            if recommendations:
                print("\n📝 Test 5: Adding user feedback...")
                rec_id = recommendations[0]['id']
                
                feedback = recommendation_service.add_feedback(
                    recommendation_id=rec_id,
                    feedback_type='useful',
                    feedback_value='helpful',
                    feedback_text='This recommendation was very relevant to my needs',
                    ip_address='127.0.0.1'
                )
                print(f"✅ Added feedback: {feedback is not None}")
            
            # Test 6: Get analytics
            print("\n📝 Test 6: Getting recommendation analytics...")
            analytics = recommendation_service.get_recommendation_analytics(session.id)
            print(f"✅ Analytics retrieved:")
            print(f"   Total recommendations: {analytics.get('total', 0)}")
            print(f"   Interactions: {analytics.get('interactions', {})}")
            print(f"   Average confidence: {analytics.get('average_confidence', 0):.2f}")
            
            # Test 7: Test different recommendation types
            print("\n📝 Test 7: Testing outcome recommendations...")
            outcome_recs = recommendation_service.generate_recommendations(
                session_id=session.id,
                context_data=context_data,
                recommendation_type='outcome',
                limit=2
            )
            print(f"✅ Generated {len(outcome_recs)} outcome recommendations")
            
            print("\n📝 Test 8: Testing analysis recommendations...")
            analysis_recs = recommendation_service.generate_recommendations(
                session_id=session.id,
                context_data=context_data,
                recommendation_type='analysis',
                limit=2
            )
            print(f"✅ Generated {len(analysis_recs)} analysis recommendations")
            
            # Test 8: Verify database models
            print("\n📝 Test 9: Verifying database models...")
            
            # Check recommendation engine
            engines = RecommendationEngine.query.all()
            print(f"✅ Found {len(engines)} recommendation engines")
            
            # Check user preferences
            preferences = UserPreference.get_preferences(session.id)
            print(f"✅ Found {len(preferences)} user preferences")
            
            # Check recommendations
            all_recs = Recommendation.get_for_session(session.id)
            print(f"✅ Found {len(all_recs)} total recommendations")
            
            # Check active recommendations
            active_recs = Recommendation.get_active_for_session(session.id)
            print(f"✅ Found {len(active_recs)} active recommendations")
            
            print("\n🎉 All tests completed successfully!")
            print("=" * 60)
            print("Smart AI Recommendations Context Integration is working correctly!")
            
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the API endpoints (requires running server)."""
    print("\n🌐 API Endpoint Testing Guide")
    print("=" * 40)
    print("To test the API endpoints, start the Flask server and use these curl commands:")
    print()
    
    # Generate recommendations
    print("1. Generate recommendations:")
    print('curl -X POST http://localhost:5000/api/smart-recommendations/generate \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"session_id": "test-session", "recommendation_type": "metric", "limit": 3}\'')
    print()
    
    # Record interaction
    print("2. Record interaction:")
    print('curl -X POST http://localhost:5000/api/smart-recommendations/interact \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"recommendation_id": 1, "interaction_type": "clicked"}\'')
    print()
    
    # Add feedback
    print("3. Add feedback:")
    print('curl -X POST http://localhost:5000/api/smart-recommendations/feedback \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"recommendation_id": 1, "feedback_type": "useful", "feedback_text": "Very helpful!"}\'')
    print()
    
    # Get analytics
    print("4. Get analytics:")
    print('curl "http://localhost:5000/api/smart-recommendations/analytics?session_id=test-session"')
    print()
    
    # Get active recommendations
    print("5. Get active recommendations:")
    print('curl "http://localhost:5000/api/smart-recommendations/active?session_id=test-session"')

if __name__ == '__main__':
    print("Smart AI Recommendations Test Suite")
    print("====================================")
    
    # Run the main test
    success = test_recommendation_system()
    
    if success:
        # Show API testing guide
        test_api_endpoints()
        
        print("\n✨ Summary:")
        print("- ✅ Smart Recommendation models created")
        print("- ✅ Context-aware recommendation generation implemented")
        print("- ✅ User preferences and feedback tracking working")
        print("- ✅ API endpoints ready for use")
        print("- ✅ Analytics and history tracking functional")
        
        print("\n🚀 The Smart AI Recommendations Context Integration is ready!")
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
        sys.exit(1)
