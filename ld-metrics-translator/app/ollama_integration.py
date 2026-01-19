"""
Ollama Integration Module for L&D Metrics Translator
Provides LLM-powered features including recommendations, report generation, and event analysis
"""

import requests
import json
import logging
import uuid
import time
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

        req_timeout = kwargs.pop('request_timeout', None)
        req_retries = kwargs.pop('request_retries', None)
        req_backoff = kwargs.pop('request_backoff', None)

        options = {}
        option_keys = {
            'temperature',
            'top_p',
            'top_k',
            'repeat_penalty',
            'seed',
            'num_ctx',
            'num_predict',
            'mirostat',
            'mirostat_eta',
            'mirostat_tau',
        }
        for key in list(option_keys):
            if key in kwargs:
                options[key] = kwargs.pop(key)
        if 'max_tokens' in kwargs and 'num_predict' not in options:
            options['num_predict'] = kwargs.pop('max_tokens')

        if 'num_ctx' not in options:
            try:
                cfg_ctx = current_app.config.get('OLLAMA_NUM_CTX')
                if cfg_ctx:
                    options['num_ctx'] = int(cfg_ctx)
            except Exception:
                pass

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if format:
            payload["format"] = format

        if options:
            payload['options'] = options

        # Remaining kwargs are treated as additional top-level Ollama fields.
        if kwargs:
            payload.update(kwargs)

        timeout = req_timeout if req_timeout is not None else current_app.config.get('OLLAMA_TIMEOUT', 120)
        max_retries = req_retries if req_retries is not None else current_app.config.get('OLLAMA_MAX_RETRIES', 1)
        max_retries = max(1, int(max_retries))
        backoff = req_backoff if req_backoff is not None else current_app.config.get('OLLAMA_RETRY_BACKOFF', 2.0)
        backoff = max(0.0, float(backoff))

        filtered_payload = {k: v for k, v in payload.items() if k != 'prompt'}
        logger.info(
            f"Sending request to Ollama with payload: {json.dumps(filtered_payload)} | timeout={timeout}s retries={max_retries}"
        )

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '').strip()
                    logger.info(
                        f"Received response from Ollama (attempt {attempt}, first 200 chars): {response_text[:200]}..."
                    )
                    return response_text

                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                raise Exception(error_msg)

            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                last_error = str(e)
                logger.warning(
                    f"Ollama request attempt {attempt} failed: {last_error}"
                )
                if attempt < max_retries:
                    sleep_time = backoff ** (attempt - 1)
                    logger.info(f"Retrying in {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Unexpected error in Ollama.generate on attempt {attempt}: {last_error}",
                    exc_info=True
                )
                break

        error_msg = f"Ollama request failed after {max_retries} attempt(s): {last_error}"
        logger.error(error_msg)
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
        self.model_name = "llama3.2:3b"
    
    def analyze_event(
        self,
        event_description: str,
        selected_metrics: List[Dict[str, Any]] | None = None,
        role_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze an event and provide L&D recommendations
        
        Args:
            event_description: Description of the workplace event to analyze
            selected_metrics: List of currently selected metrics for context-aware analysis
            role_context: Optional dict describing the selected role profile (KSAOs & targets)
        
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
                "learning_needs": [{"name": "Short title", "summary": "One sentence"}],
                "recommended_metrics": [{"name": "Metric name", "summary": "What it indicates", "category": "Optional"}],
                "interventions": [{"name": "Intervention name", "summary": "How it helps"}],
                "success_measures": [{"name": "Outcome/measure", "summary": "How to evaluate"}],
                "behavioral_biases": [
                    {
                        "name": "Bias name",
                        "description": "Brief description of how this bias appears in the event",
                        "impact": "Short sentence describing the risk created by this bias",
                        "countermeasures": ["list", "of", "practical", "countermeasures"],
                        "related_framework": "Optional learning or decision framework"
                    }
                ],
                "role_gap_analysis": [
                    {
                        "competency": "Name of the role competency or KSA",
                        "severity": "high | medium | low",
                        "target_expectation": "What the benchmark expects",
                        "observation": "What the event reveals",
                        "recommended_action": "Action to close the gap",
                        "linked_target_id": "skill:123",
                        "evidence": [
                            {"snippet": "Exact quote from the event text", "rationale": "Why this supports the observation"}
                        ]
                    }
                ]
            }
            
            Keep the response concise so it fits within the output limit:
            - learning_needs: 2 items
            - recommended_metrics: 2 items
            - interventions: 2 items
            - success_measures: 2 items
            - behavioral_biases: 2 items
            - role_gap_analysis: 2 items max (only if role context provided)

            IMPORTANT rules:
            - Do NOT output null for required fields. Use an empty string only if truly unknown.
            - If ROLE PROFILE CONTEXT is provided, role_gap_analysis MUST be a non-empty list.
            - When role_gap_analysis is present, every item MUST include:
              competency, severity, target_expectation, observation, recommended_action, linked_target_id, evidence.
            - linked_target_id MUST match one of the bracketed IDs provided in ROLE PROFILE CONTEXT.
            - evidence MUST include at least one snippet that is an exact quote from the event text.
            - Output MUST be strict JSON:
              - Use double quotes for all JSON keys and string values.
              - Escape any double quotes inside string values as \".
              - Do not include raw newline characters inside string values.

            Return only valid JSON. Do not include markdown, commentary, or trailing text."""

            def _extract_json_candidate(text: str) -> str | None:
                if not text:
                    return None
                start = text.find('{')
                end = text.rfind('}')
                if start == -1 or end == -1 or end <= start:
                    return None
                candidate = text[start:end + 1].strip()
                return candidate if candidate else None

            def _parse_json_response(text: str) -> Dict[str, Any]:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    candidate = _extract_json_candidate(text)
                    if candidate and candidate != text:
                        return json.loads(candidate)
                    raise

            def _norm_for_quote_match(text: str) -> str:
                try:
                    s = str(text or "")
                    # Normalize common unicode quotes to ASCII
                    s = s.replace("\u201c", '"').replace("\u201d", '"')
                    s = s.replace("\u2018", "'").replace("\u2019", "'")
                    # Normalize common dash variants
                    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
                    # Collapse whitespace
                    s = " ".join(s.split())
                    return s.lower()
                except Exception:
                    return ""

            def _role_gaps_complete(payload: Dict[str, Any]) -> bool:
                gaps = payload.get("role_gap_analysis")
                if not isinstance(gaps, list) or not gaps:
                    return False

                def _clean_snippet(s: str) -> str:
                    try:
                        t = str(s or "").strip()
                        if not t:
                            return ""
                        if t.startswith("```") and t.endswith("```"):
                            t = t[3:-3].strip()
                        t = t.strip("\"'`“”‘’ ")
                        for prefix in ("- ", "• ", "* ", "> "):
                            if t.startswith(prefix):
                                t = t[len(prefix):].strip()
                        return t
                    except Exception:
                        return ""

                event_norm = _norm_for_quote_match(event_description)
                for g in gaps:
                    if not isinstance(g, dict):
                        return False
                    if not g.get("linked_target_id"):
                        return False
                    if not g.get("observation") or not g.get("recommended_action"):
                        return False
                    ev = g.get("evidence")
                    if not isinstance(ev, list) or not ev:
                        return False
                    has_quote = False
                    for item in ev:
                        if isinstance(item, dict) and (item.get("snippet") or item.get("quote") or item.get("text")):
                            snippet = _clean_snippet(item.get("snippet") or item.get("quote") or item.get("text"))
                            if not snippet:
                                continue
                            if "..." in snippet or "…" in snippet:
                                continue
                            if snippet in event_description:
                                has_quote = True
                                break
                            sn = _norm_for_quote_match(snippet)
                            if sn and len(sn) >= 12 and sn in event_norm:
                                has_quote = True
                                break
                        if isinstance(item, str) and item.strip():
                            snippet = _clean_snippet(item)
                            if "..." in snippet or "…" in snippet:
                                continue
                            if snippet in event_description:
                                has_quote = True
                                break
                            sn = _norm_for_quote_match(snippet)
                            if sn and len(sn) >= 12 and sn in event_norm:
                                has_quote = True
                                break
                    if not has_quote:
                        return False
                return True

            def _try_regenerate_role_gaps(payload: Dict[str, Any]) -> tuple[bool, bool]:
                if not role_context:
                    return (False, False)
                if _role_gaps_complete(payload):
                    return (False, True)
                attempted = True
                targets = role_context.get("ksao_targets") or []
                allowed_lines = []
                for t in targets[:12]:
                    tid = t.get("target_id")
                    if not tid:
                        continue
                    nm = t.get("name") or "Target"
                    kd = t.get("kind") or "target"
                    lvl = t.get("target_level")
                    suffix = f" (target {lvl}/5)" if lvl is not None else ""
                    allowed_lines.append(f"- {tid}: {kd}: {nm}{suffix}")
                allowed_block = "\n".join(allowed_lines) if allowed_lines else "- (no targets provided)"
                gap_fix_prompt = (
                    "Generate ONLY a JSON object with a single key 'role_gap_analysis' (a list).\n\n"
                    "ROLE PROFILE TARGETS (linked_target_id MUST be one of these IDs):\n"
                    f"{allowed_block}\n\n"
                    "EVENT TEXT:\n"
                    f"{event_description}\n\n"
                    "Create 2-3 role_gap_analysis items. Each item MUST include:\n"
                    "- competency (string)\n"
                    "- severity (high|medium|low)\n"
                    "- target_expectation (string)\n"
                    "- observation (string)\n"
                    "- recommended_action (string)\n"
                    "- linked_target_id (must match one of the provided IDs)\n"
                    "- evidence: an array with at least 1 object {snippet, rationale}, where snippet is an exact contiguous quote from EVENT TEXT (copy-paste).\n"
                    "  Do NOT paraphrase. Do NOT use ellipses (no '...' and no '…').\n\n"
                    "Return only valid JSON."
                )
                gap_fix = self.ollama.generate(
                    model=self.model_name,
                    prompt=gap_fix_prompt,
                    system_prompt="You output strict JSON only. Do not omit required keys. Do not use null.",
                    format="json",
                    temperature=0.0,
                    num_predict=450,
                    num_ctx=8192,
                    keep_alive="30m",
                    request_timeout=180,
                    request_retries=1,
                    request_backoff=0.0,
                )
                if not gap_fix:
                    # Force fallback gaps if role context exists but model won't comply
                    payload["role_gap_analysis"] = []
                    return (attempted, False)
                try:
                    gap_fix_obj = _parse_json_response(gap_fix)
                    new_gaps = gap_fix_obj.get("role_gap_analysis")
                    if isinstance(new_gaps, list) and new_gaps:
                        def _event_evidence_fallback() -> list[dict[str, Any]]:
                            try:
                                if not isinstance(event_description, str) or not event_description:
                                    return []
                                lines = [ln for ln in event_description.splitlines() if ln]
                                snippet = (lines[0] if lines else event_description)[:240]
                                snippet = str(snippet or "").strip()
                                if not snippet:
                                    return []
                                return [{"snippet": snippet, "rationale": "Direct excerpt from the event description."}]
                            except Exception:
                                return []

                        def _clean_snippet_local(s: Any) -> str:
                            try:
                                t = str(s or "").strip()
                                if not t:
                                    return ""
                                if t.startswith("```") and t.endswith("```"):
                                    t = t[3:-3].strip()
                                t = t.strip("\"'`“”‘’ ")
                                for prefix in ("- ", "• ", "* ", "> "):
                                    if t.startswith(prefix):
                                        t = t[len(prefix):].strip()
                                return t
                            except Exception:
                                return ""

                        def _evidence_has_valid_quote(ev: Any) -> bool:
                            if not isinstance(ev, list) or not ev:
                                return False
                            event_norm = _norm_for_quote_match(event_description)
                            for item in ev:
                                if isinstance(item, dict):
                                    raw = item.get("snippet") or item.get("quote") or item.get("text")
                                else:
                                    raw = item
                                snippet = _clean_snippet_local(raw)
                                if not snippet:
                                    continue
                                if "..." in snippet or "…" in snippet:
                                    continue
                                if snippet in event_description:
                                    return True
                                sn = _norm_for_quote_match(snippet)
                                if sn and len(sn) >= 12 and sn in event_norm:
                                    return True
                            return False

                        injected = _event_evidence_fallback()
                        if injected:
                            for g in new_gaps:
                                if not isinstance(g, dict):
                                    continue
                                ev = g.get("evidence")
                                if not _evidence_has_valid_quote(ev):
                                    if isinstance(ev, list):
                                        g["evidence"] = ev + injected
                                    else:
                                        g["evidence"] = injected
                        payload["role_gap_analysis"] = new_gaps
                except Exception:
                    payload["role_gap_analysis"] = []
                    return (attempted, False)

                applied = _role_gaps_complete(payload)
                if not applied:
                    # If still incomplete, clear so _normalize_analysis falls back to role targets.
                    payload["role_gap_analysis"] = []
                return (attempted, applied)
            
            # Build context-aware prompt
            context_sections = []
            if selected_metrics and len(selected_metrics) > 0:
                metric_names = [m.get('name', 'Unknown') for m in selected_metrics]
                metric_categories = list(set([m.get('category', 'Unknown') for m in selected_metrics]))
                context_sections.append(
                    """
            CONTEXT: The user has already selected these metrics for tracking:
            - Selected Metrics: {metric_list}
            - Metric Categories: {category_list}
            
            Please consider these existing selections when making recommendations and try to:
            1. Build upon or complement the selected metrics
            2. Suggest interventions that align with the metric categories
            3. Identify gaps that the current metrics might not cover
            """.format(metric_list=', '.join(metric_names), category_list=', '.join(metric_categories))
                )
            if role_context:
                context_sections.append(self._summarize_role_context_for_prompt(role_context))
            context_info = "\n\n".join(section.strip() for section in context_sections if section)
            context_info = f"\n\n{context_info}" if context_info else ""
            
            user_prompt = f"""Analyze this workplace event and provide L&D recommendations:
            
            Event: {event_description}{context_info}
            
            Focus on identifying:
            1. Specific learning and development needs
            2. Relevant metrics to track impact (consider existing selections and, if provided, the role profile)
            3. Potential L&D interventions that align with the context
            4. Success measures for evaluation
            5. Role-specific gaps when a role profile is supplied
            
            Return only valid JSON with the specified format."""
            
            logger.info(f"[{req_id}] Sending request to Ollama")
            response = self.ollama.generate(
                model=self.model_name,
                prompt=user_prompt,
                system_prompt=system_prompt,
                format="json",
                temperature=0.0,
                num_predict=900,
                num_ctx=8192,
                keep_alive="30m",
                request_timeout=180,
                request_retries=2,
                request_backoff=1.5,
            )
            
            # Process and validate response
            if not response:
                raise ValueError("Empty response from Ollama")
                
            try:
                analysis_raw = _parse_json_response(response)

                # Validate response structure
                required_keys = ["learning_needs", "recommended_metrics", "interventions", "success_measures"]
                for key in required_keys:
                    if key not in analysis_raw:
                        raise ValueError(f"Missing required key in response: {key}")
                    if not isinstance(analysis_raw[key], list):
                        raise ValueError(f"Expected list for key '{key}', got {type(analysis_raw[key])}")
                # Ensure behavioral_biases exists even if empty
                if "behavioral_biases" not in analysis_raw or not isinstance(analysis_raw.get("behavioral_biases"), list):
                    analysis_raw["behavioral_biases"] = []

                role_gap_regen_attempted = False
                role_gap_regen_applied = False
                if role_context:
                    role_gap_regen_attempted, role_gap_regen_applied = _try_regenerate_role_gaps(analysis_raw)

                normalized = self._normalize_analysis(
                    analysis_raw,
                    selected_metrics,
                    role_context=role_context,
                    event_description=event_description,
                    extra_meta={
                        "role_gap_regen_attempted": role_gap_regen_attempted,
                        "role_gap_regen_applied": role_gap_regen_applied,
                    },
                )
                logger.info(f"[{req_id}] Analysis completed successfully")
                return normalized
                
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[{req_id}] Invalid JSON response from Ollama: {e}. Attempting repair. First 300 chars: {response[:300]!r}"
                )
                raw_for_repair = response
                if isinstance(raw_for_repair, str) and len(raw_for_repair) > 8000:
                    raw_for_repair = raw_for_repair[:8000]
                repair_prompt = (
                    "Fix the following so it becomes a single valid JSON object that matches the required schema.\n\n"
                    f"{raw_for_repair}\n\n"
                    "Return only valid JSON."
                )
                repaired = self.ollama.generate(
                    model=self.model_name,
                    prompt=repair_prompt,
                    system_prompt="You are a strict JSON repair tool. Output only valid JSON.",
                    format="json",
                    temperature=0.0,
                    num_predict=900,
                    num_ctx=8192,
                    keep_alive="30m",
                    request_timeout=180,
                    request_retries=2,
                    request_backoff=1.5,
                )
                if not repaired:
                    raise ValueError(f"Invalid JSON response from Ollama: {str(e)}")
                try:
                    analysis_raw = _parse_json_response(repaired)
                except json.JSONDecodeError as repair_err:
                    logger.warning(
                        f"[{req_id}] JSON repair output still invalid: {repair_err}. Falling back to strict regeneration."
                    )
                    regen = self.ollama.generate(
                        model=self.model_name,
                        prompt=user_prompt,
                        system_prompt=(
                            system_prompt
                            + "\n\nIMPORTANT: The previous output was invalid. Generate a NEW response from scratch that is strictly valid JSON and matches the schema. Return only JSON."
                        ),
                        format="json",
                        temperature=0.0,
                        num_predict=900,
                        num_ctx=8192,
                        keep_alive="30m",
                        request_timeout=180,
                        request_retries=1,
                        request_backoff=0.0,
                    )
                    if not regen:
                        raise ValueError(f"Invalid JSON response from Ollama: {str(e)}")
                    analysis_raw = _parse_json_response(regen)

                role_gap_regen_attempted = False
                role_gap_regen_applied = False
                if role_context:
                    role_gap_regen_attempted, role_gap_regen_applied = _try_regenerate_role_gaps(analysis_raw)
                normalized = self._normalize_analysis(
                    analysis_raw,
                    selected_metrics,
                    role_context=role_context,
                    event_description=event_description,
                    extra_meta={
                        "role_gap_regen_attempted": role_gap_regen_attempted,
                        "role_gap_regen_applied": role_gap_regen_applied,
                    },
                )
                logger.info(f"[{req_id}] Analysis completed successfully after repair")
                return normalized
            except Exception as e:
                raise ValueError(f"Error processing Ollama response: {str(e)}")
            
        except Exception as e:
            logger.error(f"[{req_id}] Analysis failed: {str(e)}", exc_info=True)
            raise

    def _normalize_analysis(
        self,
        analysis_raw: Dict[str, Any],
        selected_metrics: Optional[List[Dict[str, Any]]] = None,
        *,
        role_context: Optional[Dict[str, Any]] = None,
        event_description: Optional[str] = None,
        source_override: Optional[str] = None,
        error: Optional[str] = None,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Coerce LLM analysis into structured objects for consistent rendering."""

        def _normalize_list(items: Any, section: str) -> List[Dict[str, Any]]:
            normalized: List[Dict[str, Any]] = []
            if not isinstance(items, list):
                return normalized

            for entry in items:
                if entry is None:
                    continue

                original = entry
                item: Dict[str, Any] = {
                    "name": None,
                    "summary": None,
                    "details": None,
                    "success_measure": None,
                    "confidence": None,
                    "category": None,
                    "raw": original
                }

                if isinstance(entry, dict):
                    # Prefer common keys first
                    item["name"] = entry.get("name") or entry.get("title") or entry.get("metric") or entry.get("need") or entry.get("topic") or entry.get("intervention")
                    item["summary"] = entry.get("summary") or entry.get("description") or entry.get("why") or entry.get("benefit")
                    item["details"] = entry.get("details") or entry.get("context") or entry.get("notes")
                    item["success_measure"] = entry.get("success_measure") or entry.get("measure") or entry.get("target")
                    item["confidence"] = entry.get("confidence")
                    item["category"] = entry.get("category") or entry.get("type") or entry.get("kind")
                else:
                    value = str(entry).strip()
                    # Attempt to split on colon or hyphen to separate name and summary
                    delimiter = ":" if ":" in value else " - " if " - " in value else None
                    if delimiter:
                        parts = [part.strip() for part in value.split(delimiter, 1)]
                        if len(parts) == 2:
                            item["name"], item["summary"] = parts[0], parts[1]
                        else:
                            item["name"] = value
                    else:
                        item["name"] = value

                # Final fallbacks
                if not item["name"] and item["summary"]:
                    item["name"] = item["summary"]
                    item["summary"] = None

                if not item["name"]:
                    continue

                # Section-specific hints
                if section == "recommended_metrics" and not item["category"] and selected_metrics:
                    categories = {
                        str(m.get("name")).strip().lower(): m.get("category")
                        for m in selected_metrics if isinstance(m, dict)
                    }
                    key = item["name"].strip().lower()
                    if key in categories:
                        item["category"] = categories[key]

                item["section"] = section
                normalized.append(item)

            return normalized

        def _normalize_biases(items: Any) -> List[Dict[str, Any]]:
            normalized: List[Dict[str, Any]] = []
            if not isinstance(items, list):
                return normalized
            for entry in items:
                if entry is None:
                    continue
                bias: Dict[str, Any] = {
                    "name": None,
                    "description": None,
                    "impact": None,
                    "countermeasures": [],
                    "related_framework": None,
                    "raw": entry
                }
                if isinstance(entry, dict):
                    bias["name"] = entry.get("name") or entry.get("title") or entry.get("bias")
                    bias["description"] = entry.get("description") or entry.get("summary") or entry.get("why")
                    bias["impact"] = entry.get("impact") or entry.get("effect")
                    cm = entry.get("countermeasures") or entry.get("mitigations") or entry.get("actions")
                    if isinstance(cm, list):
                        bias["countermeasures"] = [str(x).strip() for x in cm if x]
                    elif isinstance(cm, str) and cm.strip():
                        bias["countermeasures"] = [cm.strip()]
                    bias["related_framework"] = entry.get("related_framework") or entry.get("framework") or entry.get("model")
                else:
                    text = str(entry).strip()
                    if text:
                        bias["name"] = text
                if not bias["name"]:
                    continue
                normalized.append(bias)
            return normalized

        normalized_learning_needs = _normalize_list(analysis_raw.get("learning_needs", []), "learning_needs")
        normalized_metrics = _normalize_list(analysis_raw.get("recommended_metrics", []), "recommended_metrics")
        normalized_interventions = _normalize_list(analysis_raw.get("interventions", []), "interventions")
        normalized_success = _normalize_list(analysis_raw.get("success_measures", []), "success_measures")
        normalized_biases = _normalize_biases(analysis_raw.get("behavioral_biases", []))

        role_gap_items = self._normalize_role_gaps(analysis_raw.get("role_gap_analysis"))

        def _clean_snippet_local(s: Any) -> str:
            try:
                t = str(s or "").strip()
                if not t:
                    return ""
                if t.startswith("```") and t.endswith("```"):
                    t = t[3:-3].strip()
                t = t.strip("\"'`“”‘’ ")
                for prefix in ("- ", "• ", "* ", "> "):
                    if t.startswith(prefix):
                        t = t[len(prefix):].strip()
                return t
            except Exception:
                return ""

        def _excerpt_from_event_for(snippet: str) -> str:
            try:
                if not isinstance(event_description, str) or not event_description:
                    return ""
                if not snippet:
                    return ""
                if "..." in snippet or "…" in snippet:
                    return ""

                MAX_LEN = 240

                def _clip_exact(text: str) -> str:
                    t = str(text or "")
                    if not t:
                        return ""
                    if len(t) <= MAX_LEN:
                        return t
                    cut = t[:MAX_LEN]
                    if cut and cut[-1].isalnum():
                        sp = cut.rfind(" ")
                        if sp >= 40:
                            cut = cut[:sp]
                    return cut.rstrip()

                def _sentence_around_index(idx: int) -> str:
                    try:
                        if idx < 0:
                            return ""
                        s = event_description
                        breaks = ".!?\n"
                        left = -1
                        for ch in breaks:
                            left = max(left, s.rfind(ch, 0, idx))
                        start = left + 1 if left >= 0 else 0
                        right = len(s)
                        for ch in breaks:
                            r = s.find(ch, idx)
                            if r != -1:
                                right = min(right, r + 1)
                        sent = s[start:right].strip()
                        if not sent:
                            return ""
                        if len(sent) <= MAX_LEN:
                            return sent
                        rel = idx - start
                        w_start = max(0, rel - 60)
                        w_end = min(len(sent), rel + 160)
                        piece = sent[w_start:w_end]
                        piece = piece.strip()
                        piece = _clip_exact(piece)
                        return piece
                    except Exception:
                        return ""

                if snippet in event_description:
                    if len(snippet) <= MAX_LEN:
                        return snippet
                    snip_lower = snippet.lower()
                    anchor_idx = event_description.lower().find(snip_lower[: max(10, min(40, len(snip_lower)))])
                    if anchor_idx >= 0:
                        sent = _sentence_around_index(anchor_idx)
                        if sent:
                            return sent
                    return _clip_exact(snippet)

                event_lower = event_description.lower()

                variants = [
                    snippet,
                    snippet.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'"),
                    snippet.replace('"', "").replace("'", "").replace("\u201c", "").replace("\u201d", "").replace("\u2018", "").replace("\u2019", ""),
                ]
                for v in variants:
                    v = str(v or "").strip()
                    if v and v in event_description:
                        return _clip_exact(v)

                raw_tokens = [tok.strip("\"'`“”‘’.,;:()[]{}") for tok in snippet.replace("\n", " ").split()]
                tokens = [t for t in raw_tokens if t and any(ch.isalnum() for ch in t)]
                tokens.sort(key=len, reverse=True)
                anchor = None
                for t in tokens:
                    tl = t.lower()
                    if len(tl) < 6:
                        continue
                    if tl in event_lower:
                        anchor = t
                        break
                if not anchor:
                    for t in tokens:
                        tl = t.lower()
                        if tl and tl in event_lower:
                            anchor = t
                            break
                if not anchor:
                    return ""

                idx = event_lower.find(anchor.lower())
                if idx < 0:
                    return ""

                sent = _sentence_around_index(idx)
                if sent:
                    return sent

                start = max(0, idx - 60)
                end = min(len(event_description), idx + len(anchor) + 160)
                excerpt = event_description[start:end].strip()
                return _clip_exact(excerpt)
            except Exception:
                return ""

        def _repair_gap_evidence(g: Dict[str, Any]) -> None:
            try:
                if not isinstance(g, dict):
                    return
                ev = g.get("evidence")
                if not isinstance(ev, list) or not ev:
                    return
                repaired: list[dict[str, Any]] = []
                for item in ev:
                    if not isinstance(item, dict):
                        continue
                    raw = item.get("snippet") or item.get("quote") or item.get("text")
                    rationale = item.get("rationale") or item.get("reason") or item.get("explanation")
                    snippet = _clean_snippet_local(raw)
                    if not snippet:
                        continue
                    excerpt = _excerpt_from_event_for(snippet)
                    if not excerpt:
                        continue
                    repaired.append({"snippet": excerpt, "rationale": str(rationale).strip() if rationale else None})
                g["evidence"] = repaired
            except Exception:
                return

        def _gap_complete(g: Dict[str, Any]) -> bool:
            if not isinstance(g, dict):
                return False
            if not g.get("linked_target_id"):
                return False
            if not g.get("observation") or not g.get("recommended_action"):
                return False
            ev = g.get("evidence")
            if not isinstance(ev, list) or not ev:
                return False
            for item in ev:
                if not isinstance(item, dict):
                    continue
                raw = item.get("snippet") or item.get("quote") or item.get("text")
                snippet = _clean_snippet_local(raw)
                if not snippet:
                    continue
                excerpt = _excerpt_from_event_for(snippet)
                if excerpt:
                    return True
            return False

        fallback_used = False

        if isinstance(event_description, str) and event_description and role_gap_items:
            for g in role_gap_items:
                _repair_gap_evidence(g)

        relinked_count = 0
        observation_rewritten_count = 0
        if role_context and isinstance(event_description, str) and event_description and role_gap_items:
            targets = role_context.get("ksao_targets") or []
            if isinstance(targets, list) and targets:
                target_by_id: Dict[str, Dict[str, Any]] = {}
                for t in targets:
                    if not isinstance(t, dict):
                        continue
                    tid = t.get("target_id")
                    if tid:
                        target_by_id[str(tid)] = t

                def _tokenize(text: Any) -> set[str]:
                    try:
                        s = str(text or "").lower()
                        out: set[str] = set()
                        buf: list[str] = []
                        for ch in s:
                            if ch.isalnum():
                                buf.append(ch)
                            else:
                                if buf:
                                    out.add("".join(buf))
                                    buf = []
                        if buf:
                            out.add("".join(buf))
                        stop = {
                            "the","and","or","to","of","a","an","in","on","for","with","without","by","from","is","are",
                            "was","were","be","been","being","this","that","these","those","it","as","at","into","over",
                            "during","later","then","when","while","instead","due","did","not","just","quickly",
                        }
                        out = {w for w in out if len(w) >= 4 and w not in stop}
                        return out
                    except Exception:
                        return set()

                def _gap_text(g: Dict[str, Any]) -> str:
                    try:
                        parts: list[str] = []
                        ev = g.get("evidence")
                        if isinstance(ev, list):
                            for item in ev[:3]:
                                if isinstance(item, dict) and item.get("snippet"):
                                    parts.append(str(item.get("snippet")))
                        for k in ("observation", "recommended_action"):
                            v = g.get(k)
                            if v:
                                parts.append(str(v))
                        if not parts:
                            for k in ("competency", "target_expectation"):
                                v = g.get(k)
                                if v:
                                    parts.append(str(v))
                        return " ".join(parts)
                    except Exception:
                        return ""

                def _gap_evidence_text(g: Dict[str, Any]) -> str:
                    try:
                        parts: list[str] = []
                        ev = g.get("evidence")
                        if isinstance(ev, list):
                            for item in ev[:4]:
                                if isinstance(item, dict) and item.get("snippet"):
                                    parts.append(str(item.get("snippet")))
                        return " ".join(parts)
                    except Exception:
                        return ""

                def _rewrite_observation_if_needed(g: Dict[str, Any]) -> bool:
                    try:
                        obs = str(g.get("observation") or "").strip()
                        exp = str(g.get("target_expectation") or "").strip()

                        ev_text = _gap_evidence_text(g)
                        ev_toks = _tokenize(ev_text)
                        obs_toks = _tokenize(obs)
                        exp_toks = _tokenize(exp)

                        needs = False
                        if not obs or len(obs) < 12:
                            needs = True
                        elif exp and obs.lower() == exp.lower():
                            needs = True
                        elif exp_toks and obs_toks and len(obs_toks) >= 4 and obs_toks == exp_toks:
                            needs = True
                        elif ev_toks and (not obs_toks or len(obs_toks.intersection(ev_toks)) < 1):
                            needs = True

                        if not needs:
                            return False

                        ev = g.get("evidence")
                        snippet = ""
                        if isinstance(ev, list) and ev:
                            first = ev[0]
                            if isinstance(first, dict) and first.get("snippet"):
                                snippet = str(first.get("snippet") or "").strip()
                        if not snippet:
                            return False

                        if len(snippet) > 220:
                            snippet = snippet[:220].rstrip()
                        g["observation"] = f"Observed: {snippet}"
                        return True
                    except Exception:
                        return False

                def _target_cats(t: Dict[str, Any]) -> set[str]:
                    try:
                        tname = str(t.get("name") or "")
                        tkind = str(t.get("kind") or "")
                        ttext = f"{tkind} {tname}".strip()
                        ttoks = _tokenize(ttext)
                        cats: set[str] = set()
                        if {"safety", "incident", "procedure", "procedures", "sop"}.intersection(ttoks):
                            cats.add("safety")
                        if {"quality", "defect", "verification", "verify", "checks", "check"}.intersection(ttoks):
                            cats.add("quality")
                        if {"handover", "handoff", "briefing"}.intersection(ttoks):
                            cats.add("handover")
                        if {"plan", "planning", "allocation", "prioritization", "priority", "backlog", "output"}.intersection(ttoks):
                            cats.add("planning")
                        if {"conflict", "deescalation", "deescalate", "deescal", "voice"}.intersection(ttoks):
                            cats.add("conflict")
                        return cats
                    except Exception:
                        return set()

                def _gap_flags(gtext: str) -> set[str]:
                    try:
                        toks = _tokenize(gtext)
                        gl = gtext.lower()
                        flags: set[str] = set()
                        if "lockout" in gl or "tagout" in gl or "lockout/tagout" in gl:
                            flags.add("safety")
                        if {"safety", "incident", "sop"}.intersection(toks):
                            flags.add("safety")
                        if {"quality", "verification", "verify", "defect", "checks", "check"}.intersection(toks):
                            flags.add("quality")
                        if {"handover", "briefing"}.intersection(toks):
                            flags.add("handover")
                        if {"plan", "backlog", "output", "priorit"}.intersection(toks):
                            flags.add("planning")
                        if {"argued", "voice", "deescal", "de-escal", "conflict"}.intersection(toks) or "de-escal" in gl:
                            flags.add("conflict")
                        return flags
                    except Exception:
                        return set()

                def _score_target(t: Dict[str, Any], gtext: str) -> int:
                    try:
                        tname = str(t.get("name") or "")
                        tkind = str(t.get("kind") or "")
                        ttext = f"{tkind} {tname}".strip()
                        if not ttext:
                            return 0
                        gtoks = _tokenize(gtext)
                        ttoks = _tokenize(ttext)
                        if not gtoks or not ttoks:
                            return 0
                        overlap = len(gtoks.intersection(ttoks))
                        score = overlap * 2
                        gl = gtext.lower()
                        tl = ttext.lower()
                        flags = _gap_flags(gtext)
                        cats = _target_cats(t)
                        kind_l = tkind.lower().strip()
                        if "safety" in flags and "safety" in cats:
                            score += 12
                        if "quality" in flags and "quality" in cats:
                            score += 10
                        if "handover" in flags and "handover" in cats:
                            score += 9
                        if "planning" in flags and "planning" in cats:
                            score += 6
                        if "conflict" in flags and "conflict" in cats:
                            score += 8

                        if kind_l == "knowledge":
                            if "safety" in flags and "safety" in cats:
                                score += 3
                            if "quality" in flags and "quality" in cats:
                                score += 3
                        if kind_l == "skill" and "handover" in flags and "handover" in cats:
                            score += 2

                        if ("lockout" in gl or "tagout" in gl) and "safety" in cats:
                            score += 10
                        if ("verification" in gl or "quality" in gl) and "quality" in cats:
                            score += 8
                        if "handover" in gl and "handover" in cats:
                            score += 7
                        return int(score)
                    except Exception:
                        return 0

                for g in role_gap_items:
                    if not isinstance(g, dict):
                        continue
                    gtext = _gap_evidence_text(g) or _gap_text(g)
                    if not gtext:
                        continue

                    current_id = g.get("linked_target_id")
                    current_t = target_by_id.get(str(current_id)) if current_id is not None else None
                    current_score = _score_target(current_t, gtext) if current_t else 0

                    best_id = None
                    best_score = 0
                    for tid, t in target_by_id.items():
                        s = _score_target(t, gtext)
                        if s > best_score:
                            best_score = s
                            best_id = tid

                    if best_id and (best_score >= 8) and (best_score > current_score):
                        if str(g.get("linked_target_id")) != str(best_id):
                            g["linked_target_id"] = best_id
                            relinked_count += 1

                    if _rewrite_observation_if_needed(g):
                        observation_rewritten_count += 1

        if role_context and role_gap_items:
            role_gap_items = [g for g in role_gap_items if _gap_complete(g)]
        if role_context and not role_gap_items:
            fallback_used = True
            role_gap_items = self._fallback_role_gaps(role_context, normalized_learning_needs, event_description=event_description)

        context_summary = None
        if role_context:
            context_summary = {
                "id": role_context.get("id"),
                "name": role_context.get("name"),
                "department": role_context.get("department"),
            }

        normalized_payload = {
            "learning_needs": normalized_learning_needs,
            "recommended_metrics": normalized_metrics,
            "interventions": normalized_interventions,
            "success_measures": normalized_success,
            "behavioral_biases": normalized_biases,
            "role_gap_analysis": role_gap_items,
            "_meta": {
                "source": source_override or "ai",
                "normalized_at": datetime.utcnow().isoformat() + "Z",
                "error": error,
                "raw_response": analysis_raw,
                "role_context_included": bool(role_context),
                "role_context_summary": context_summary,
                "role_gap_fallback_used": bool(fallback_used),
                "role_gap_relinked_count": int(relinked_count),
                "role_gap_observation_rewritten_count": int(observation_rewritten_count),
            }
        }

        if extra_meta and isinstance(extra_meta, dict):
            try:
                normalized_payload["_meta"].update(extra_meta)
            except Exception:
                pass

        return normalized_payload

    def _normalize_role_gaps(self, items: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if not isinstance(items, list):
            return normalized
        for entry in items:
            if entry is None:
                continue
            gap: Dict[str, Any] = {
                "competency": None,
                "severity": None,
                "target_expectation": None,
                "observation": None,
                "recommended_action": None,
                "linked_target_id": None,
                "linked_competency_id": None,
                "evidence": [],
                "raw": entry,
            }
            if isinstance(entry, dict):
                gap["competency"] = entry.get("competency") or entry.get("name") or entry.get("ksa")
                gap["severity"] = entry.get("severity") or entry.get("impact_level")
                gap["target_expectation"] = entry.get("target_expectation") or entry.get("expectation") or entry.get("benchmark")
                gap["observation"] = entry.get("observation") or entry.get("gap_summary") or entry.get("issue")
                gap["recommended_action"] = entry.get("recommended_action") or entry.get("action") or entry.get("next_step")
                gap["linked_target_id"] = entry.get("linked_target_id") or entry.get("target_id") or entry.get("linked_ksa_target_id")
                link_id = entry.get("linked_competency_id") or entry.get("competency_id")
                if link_id is not None and gap.get("linked_target_id") is None:
                    try:
                        gap["linked_competency_id"] = int(link_id)
                    except Exception:
                        gap["linked_competency_id"] = link_id

                evidence = entry.get("evidence") or entry.get("evidence_snippets") or entry.get("evidence_snippet")
                if isinstance(evidence, list):
                    for ev in evidence:
                        if ev is None:
                            continue
                        if isinstance(ev, dict):
                            snippet = ev.get("snippet") or ev.get("quote") or ev.get("text")
                            rationale = ev.get("rationale") or ev.get("reason") or ev.get("explanation")
                            if snippet:
                                gap["evidence"].append({"snippet": str(snippet).strip(), "rationale": str(rationale).strip() if rationale else None})
                        else:
                            s = str(ev).strip()
                            if s:
                                gap["evidence"].append({"snippet": s, "rationale": None})
                elif isinstance(evidence, dict):
                    snippet = evidence.get("snippet") or evidence.get("quote") or evidence.get("text")
                    rationale = evidence.get("rationale") or evidence.get("reason") or evidence.get("explanation")
                    if snippet:
                        gap["evidence"].append({"snippet": str(snippet).strip(), "rationale": str(rationale).strip() if rationale else None})
                elif isinstance(evidence, str) and evidence.strip():
                    gap["evidence"].append({"snippet": evidence.strip(), "rationale": None})
            else:
                text = str(entry).strip()
                if text:
                    gap["competency"] = text
                    gap["observation"] = text
            if not gap["competency"] and not gap["observation"]:
                continue
            normalized.append(gap)
        return normalized

    def _fallback_role_gaps(
        self,
        role_context: Dict[str, Any],
        learning_needs: List[Dict[str, Any]],
        *,
        event_description: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        targets = role_context.get("ksao_targets") or []
        need_names = [n.get("name") for n in learning_needs if isinstance(n, dict) and n.get("name")]
        fallback: List[Dict[str, Any]] = []

        evidence_items: List[Dict[str, Any]] = []
        if isinstance(event_description, str) and event_description:
            # Use exact excerpts from the event text (no rewriting) so fallback remains auditable.
            lines = [ln for ln in event_description.splitlines() if ln]
            if lines:
                snippet = lines[0][:240]
            else:
                snippet = event_description[:240]
            if snippet:
                evidence_items = [{"snippet": snippet, "rationale": "Direct excerpt from the event description."}]

        for idx, target in enumerate(targets[:3]):
            comp_name = target.get("name")
            if not comp_name:
                comp_name = f"Role benchmark #{idx + 1}"
            expectation = target.get("target_level")
            expectation_text = f"Target level {expectation}/5" if expectation else "Benchmark expectation from role profile"
            observation = None
            if need_names:
                observation = f"Event highlights learning need around {need_names[idx % len(need_names)]}."
            fallback.append({
                "competency": comp_name,
                "severity": "medium" if idx else "high",
                "target_expectation": expectation_text,
                "observation": observation or "Event indicates potential deviation from this benchmark.",
                "recommended_action": "Discuss expectation with the individual and design coaching focused on this competency.",
                "linked_target_id": target.get("target_id"),
                "evidence": evidence_items,
            })
        return fallback

    def _summarize_role_context_for_prompt(self, role_context: Dict[str, Any]) -> str:
        name = role_context.get("name") or "Selected Role"
        dept = role_context.get("department")
        lines = ["ROLE PROFILE CONTEXT:"]
        lines.append(f"- Role Name: {name}")
        if dept:
            lines.append(f"- Department: {dept}")
        def _collect_names(key, limit=4):
            items = role_context.get(key) or []
            return [item.get("name") for item in items if item.get("name")] [:limit]
        for label, key in (("Knowledge", "knowledge"), ("Skills", "skills"), ("Abilities", "abilities"), ("Outcomes", "outcomes")):
            names = _collect_names(key)
            if names:
                lines.append(f"- {label}: {', '.join(names)}")
        ksao_targets = role_context.get("ksao_targets") or []
        if ksao_targets:
            target_summaries = []
            for target in ksao_targets[:7]:
                tid = target.get("target_id")
                tname = target.get("name") or "Target"
                tkind = target.get("kind")
                lvl = target.get("target_level")
                label = f"{tname}"
                if tkind:
                    label = f"{tkind}: {label}"
                if lvl is not None:
                    label = f"{label} (target {lvl}/5)"
                if tid:
                    label = f"{label} [{tid}]"
                target_summaries.append(label)
            if target_summaries:
                lines.append("- KSAO Benchmark Targets (use linked_target_id exactly as shown): " + "; ".join(target_summaries))
        lines.append("Use this role context to judge gaps between the described event and expectations.")
        return "\n".join(lines)


# Initialize global instances
recommendation_engine = LDRecommendationEngine()
report_generator = LDReportGenerator()
event_analyzer = EventAnalyzer()
