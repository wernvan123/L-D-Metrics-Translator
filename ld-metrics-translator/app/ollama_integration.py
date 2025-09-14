"""
Ollama Integration Module for L&D Metrics Translator
Provides LLM-powered features including recommendations, report generation, and event analysis
"""

import requests
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with Ollama LLM"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available = False
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running and available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            self.available = response.status_code == 200
            logger.info(f"Ollama availability: {self.available}")
            return self.available
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama not available: {e}")
            self.available = False
            return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        if not self.available:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
        return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        if not self.available:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get('status') == 'success':
                        logger.info(f"Successfully pulled model: {model_name}")
                        return True
                    elif 'error' in data:
                        logger.error(f"Error pulling model: {data['error']}")
                        return False
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
        return False
    
    def generate(self, model: str, prompt: str, system_prompt: str = None, format: str = None, **kwargs) -> Optional[str]:
        """Generate text using Ollama
        
        Args:
            model: The model to use for generation
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt to guide the model's behavior
            format: Optional format for the response (e.g., 'json')
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            The generated text, or None if an error occurred
        """
        if not self.available:
            logger.warning("Ollama not available, falling back to rules-based system")
            return None
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            if format:
                payload["format"] = format
            
            logger.info(f"Sending request to Ollama with payload: {json.dumps({k: v for k, v in payload.items() if k != 'prompt'})}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Increased timeout for complex prompts
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').strip()
                logger.info(f"Received response from Ollama (first 200 chars): {response_text[:200]}...")
                return response_text
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "Ollama API request timed out. The model might be taking too long to respond."
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with Ollama: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error in Ollama.generate: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)


class LDRecommendationEngine:
    """L&D Recommendation Engine with LLM and rules-based fallback"""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.model_name = "llama2-uncensored:7b"  # Lightweight model for recommendations
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt for L&D recommendations"""
        return """You are an expert Learning & Development consultant specializing in metrics and analytics. 
        Your role is to provide intelligent recommendations for L&D metrics based on user selections and context.
        
        Focus on:
        - Employee engagement and behavioral metrics
        - Training effectiveness and completion rates
        - Neuroscience-based learning metrics
        - Practical, actionable recommendations
        - Systems thinking approach to L&D
        
        Always provide concise, professional recommendations with clear reasoning."""
    
    def generate_recommendations(self, selections: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """Generate intelligent recommendations based on user selections"""
        
        # Try LLM first
        llm_recommendations = self._generate_llm_recommendations(selections, context)
        if llm_recommendations:
            return llm_recommendations
        
        # Fallback to rules-based system
        return self._generate_rules_based_recommendations(selections, context)
    
    def _generate_llm_recommendations(self, selections: Dict[str, Any], context: str) -> Optional[Dict[str, Any]]:
        """Generate recommendations using LLM"""
        if not self.ollama.available:
            return None
        
        prompt = f"""
        Based on the following L&D context and user selections, provide 3 specific metric recommendations:
        
        User Selections:
        - Categories: {selections.get('categories', [])}
        - Outcomes: {selections.get('outcomes', [])}
        - Context: {context}
        
        Provide recommendations in this format:
        1. **Metric Name**: Brief description and why it's relevant
        2. **Metric Name**: Brief description and why it's relevant  
        3. **Metric Name**: Brief description and why it's relevant
        
        Focus on practical, measurable metrics that align with the selected categories and outcomes.
        """
        
        response = self.ollama.generate(self.model_name, prompt, self.system_prompt)
        if response:
            return self._parse_llm_response(response)
        
        return None
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured recommendations"""
        recommendations = {
            'items': [],
            'insights': [
                {
                    'title': 'AI-Generated Recommendations',
                    'content': 'These recommendations were generated using advanced AI analysis of your selections.',
                    'type': 'info'
                }
            ]
        }
        
        # Simple parsing - in production, you'd want more robust parsing
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.')):
                if '**' in line:
                    parts = line.split('**')
                    if len(parts) >= 3:
                        title = parts[1].strip()
                        description = parts[2].replace(':', '').strip()
                        
                        recommendations['items'].append({
                            'title': title,
                            'type': 'ai_generated',
                            'reasoning': description,
                            'priority': 'high',
                            'metrics': [title]
                        })
        
        return recommendations
    
    def _generate_rules_based_recommendations(self, selections: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Fallback rules-based recommendations"""
        return {
            'items': [
                {
                    'title': 'Employee Engagement Score',
                    'type': 'behavioral',
                    'reasoning': 'Foundation metric that influences all other learning outcomes.',
                    'priority': 'high',
                    'metrics': ['Engagement Score', 'Participation Rate']
                },
                {
                    'title': 'Training Completion Rate',
                    'type': 'operational',
                    'reasoning': 'Essential baseline for measuring program effectiveness.',
                    'priority': 'high',
                    'metrics': ['Completion Rate', 'Drop-off Rate']
                },
                {
                    'title': 'Memory Retention Rate',
                    'type': 'neuroscience',
                    'reasoning': 'Scientific measure of actual learning effectiveness.',
                    'priority': 'medium',
                    'metrics': ['Retention Score', 'Recall Accuracy']
                }
            ],
            'insights': [
                {
                    'title': 'Rules-Based Recommendations',
                    'content': 'These are our standard recommendations. For personalized suggestions, ensure Ollama is running.',
                    'type': 'tip'
                }
            ]
        }


class LDReportGenerator:
    """Generate L&D reports using LLM"""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.model_name = "llama2-uncensored:7b"
    
    def generate_report_content(self, metrics: List[str], outcomes: List[str], context: str = "") -> str:
        """Generate report content based on selected metrics and outcomes"""
        
        system_prompt = """You are an expert L&D consultant creating comprehensive reports. 
        Use systems thinking principles and focus on practical, actionable insights.
        Structure your reports professionally with clear sections and recommendations."""
        
        prompt = f"""
        Create a comprehensive Learning & Development report based on:
        
        Selected Metrics: {', '.join(metrics)}
        L&D Outcomes: {', '.join(outcomes)}
        Context: {context}
        
        Structure the report with:
        1. Executive Summary
        2. Metrics Analysis
        3. Key Insights
        4. Recommendations
        5. Next Steps
        
        Keep it professional, actionable, and focused on systems thinking approaches to L&D.
        """
        
        if self.ollama.available:
            response = self.ollama.generate(self.model_name, prompt, system_prompt)
            if response:
                return response
        
        # Fallback template
        return self._generate_template_report(metrics, outcomes, context)
    
    def _generate_template_report(self, metrics: List[str], outcomes: List[str], context: str) -> str:
        """Generate a template-based report as fallback"""
        return f"""
        # Learning & Development Metrics Report
        
        ## Executive Summary
        This report analyzes the selected L&D metrics and their alignment with organizational outcomes.
        
        ## Selected Metrics
        {chr(10).join([f"- {metric}" for metric in metrics])}
        
        ## Target Outcomes
        {chr(10).join([f"- {outcome}" for outcome in outcomes])}
        
        ## Key Insights
        - Focus on measuring both quantitative and qualitative aspects of learning
        - Ensure metrics align with business objectives
        - Consider the interconnected nature of learning systems
        
        ## Recommendations
        1. Implement regular measurement cycles
        2. Use data to drive continuous improvement
        3. Engage stakeholders in the measurement process
        
        ## Next Steps
        - Set up measurement frameworks
        - Establish baseline metrics
        - Create regular reporting schedules
        
        *Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
        """


class EventAnalyzer:
    """Analyze natural language events and provide L&D suggestions"""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.model_name = "llama2-uncensored:7b"
    
    def analyze_event(self, event_description: str, selected_metrics: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze an event and provide L&D recommendations
        
        Args:
            event_description: Description of the workplace event to analyze
            selected_metrics: List of currently selected metrics for context-aware analysis
            
        Returns:
            Dict containing analysis results with learning needs, metrics, interventions, and success measures
        """
        req_id = str(uuid.uuid4())[:6]
        logger.info(f"[{req_id}] Starting analysis for event")
        
        # Input validation
        if not event_description or not isinstance(event_description, str):
            error_msg = "Invalid event description"
            logger.error(f"[{req_id}] {error_msg}")
            raise ValueError(error_msg)
        
        try:
            # Check Ollama availability
            if not self.ollama.available:
                error_msg = "Ollama client not available"
                logger.error(f"[{req_id}] {error_msg}")
                raise RuntimeError(error_msg)
            
            # Prepare prompts with clear instructions
            system_prompt = """You are an experienced L&D professional. Analyze the given workplace event and provide 
            specific, actionable recommendations in the following JSON format:
            {
                "learning_needs": ["list", "of", "learning", "needs"],
                "recommended_metrics": ["list", "of", "metrics"],
                "interventions": ["list", "of", "interventions"],
                "success_measures": ["list", "of", "success", "measures"]
            }
            
            Ensure each list contains 3-5 specific, actionable items."""
            
            # Build context-aware prompt
            context_info = ""
            if selected_metrics and len(selected_metrics) > 0:
                metric_names = [m.get('name', 'Unknown') for m in selected_metrics]
                metric_categories = list(set([m.get('category', 'Unknown') for m in selected_metrics]))
                context_info = f"""
            
            CONTEXT: The user has already selected these metrics for tracking:
            - Selected Metrics: {', '.join(metric_names)}
            - Metric Categories: {', '.join(metric_categories)}
            
            Please consider these existing selections when making recommendations and try to:
            1. Build upon or complement the selected metrics
            2. Suggest interventions that align with the metric categories
            3. Identify gaps that the current metrics might not cover
            """
            
            user_prompt = f"""Analyze this workplace event and provide L&D recommendations:
            
            Event: {event_description}{context_info}
            
            Focus on identifying:
            1. Specific learning and development needs
            2. Relevant metrics to track impact (consider existing selections)
            3. Potential L&D interventions that align with selected metrics
            4. Success measures for evaluation
            
            Return only valid JSON with the specified format."""
            
            logger.info(f"[{req_id}] Sending request to Ollama")
            response = self.ollama.generate(
                model=self.model_name,
                prompt=user_prompt,
                system_prompt=system_prompt,
                format="json",
                temperature=0.7,
                max_tokens=1000
            )
            
            # Process and validate response
            if not response:
                raise ValueError("Empty response from Ollama")
                
            try:
                analysis = json.loads(response)
                
                # Validate response structure
                required_keys = ["learning_needs", "recommended_metrics", "interventions", "success_measures"]
                for key in required_keys:
                    if key not in analysis:
                        raise ValueError(f"Missing required key in response: {key}")
                    if not isinstance(analysis[key], list):
                        raise ValueError(f"Expected list for key '{key}', got {type(analysis[key])}")
                
                logger.info(f"[{req_id}] Analysis completed successfully")
                return analysis
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from Ollama: {str(e)}")
            except Exception as e:
                raise ValueError(f"Error processing Ollama response: {str(e)}")
            
        except Exception as e:
            logger.error(f"[{req_id}] Analysis failed: {str(e)}", exc_info=True)
            # Return a more detailed fallback response
            return {
                "learning_needs": [
                    "Error handling and troubleshooting",
                    "System and process analysis",
                    "Technical skill development"
                ],
                "recommended_metrics": [
                    "Error rate and type frequency",
                    "System response and resolution time",
                    "User impact and satisfaction scores"
                ],
                "interventions": [
                    "Comprehensive system audit and documentation review",
                    "Targeted training on error handling and troubleshooting",
                    "Process improvement workshop"
                ],
                "success_measures": [
                    "Reduction in recurring errors",
                    "Improved system stability metrics",
                    "Increased user satisfaction scores"
                ],
                "_error": str(e),
                "_source": "fallback_due_to_error"
            }


# Initialize global instances
recommendation_engine = LDRecommendationEngine()
report_generator = LDReportGenerator()
event_analyzer = EventAnalyzer()
