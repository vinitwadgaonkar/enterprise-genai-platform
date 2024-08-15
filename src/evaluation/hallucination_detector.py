"""
Hallucination detection for AI responses.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from openai import OpenAI

logger = structlog.get_logger(__name__)


@dataclass
class HallucinationResult:
    """Result of hallucination detection."""
    is_hallucination: bool
    confidence: float
    detected_issues: List[str]
    explanation: str
    suggestions: List[str]


class HallucinationDetector:
    """Detects hallucinations in AI responses."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        
        # Patterns that might indicate hallucinations
        self.hallucination_patterns = [
            r'\b(?:I think|I believe|I assume|I guess|I suppose)\b',
            r'\b(?:might be|could be|possibly|perhaps)\b',
            r'\b(?:I\'m not sure|I don\'t know|I can\'t be certain)\b',
            r'\b(?:as far as I know|to my knowledge|I recall)\b',
            r'\b(?:I remember|I recall|I think I heard)\b'
        ]
        
        # Confidence indicators
        self.confidence_indicators = [
            r'\b(?:definitely|certainly|absolutely|surely)\b',
            r'\b(?:without a doubt|no question|clearly)\b',
            r'\b(?:I can confirm|I can verify|I know for sure)\b'
        ]
    
    def detect_hallucination(
        self, 
        response: str, 
        context: Optional[str] = None,
        use_llm: bool = True
    ) -> HallucinationResult:
        """Detect hallucinations in a response."""
        try:
            # Pattern-based detection
            pattern_issues = self._detect_pattern_issues(response)
            
            # LLM-based detection
            llm_issues = []
            if use_llm and context:
                llm_issues = self._detect_llm_issues(response, context)
            
            # Combine results
            all_issues = pattern_issues + llm_issues
            is_hallucination = len(all_issues) > 0
            
            # Calculate confidence
            confidence = self._calculate_confidence(response, all_issues)
            
            # Generate explanation and suggestions
            explanation = self._generate_explanation(all_issues)
            suggestions = self._generate_suggestions(all_issues)
            
            return HallucinationResult(
                is_hallucination=is_hallucination,
                confidence=confidence,
                detected_issues=all_issues,
                explanation=explanation,
                suggestions=suggestions
            )
        
        except Exception as e:
            logger.error(f"Hallucination detection failed: {e}")
            return HallucinationResult(
                is_hallucination=False,
                confidence=0.0,
                detected_issues=[],
                explanation=f"Detection failed: {str(e)}",
                suggestions=[]
            )
    
    def _detect_pattern_issues(self, response: str) -> List[str]:
        """Detect issues using pattern matching."""
        issues = []
        
        # Check for uncertainty patterns
        for pattern in self.hallucination_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Uncertainty detected: {pattern}")
        
        # Check for overconfidence
        for pattern in self.confidence_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Overconfidence detected: {pattern}")
        
        # Check for specific claims without evidence
        claim_patterns = [
            r'\b(?:studies show|research indicates|experts say)\b',
            r'\b(?:it is known|it is established|it is proven)\b',
            r'\b(?:according to|based on|research shows)\b'
        ]
        
        for pattern in claim_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Unsubstantiated claim: {pattern}")
        
        return issues
    
    def _detect_llm_issues(self, response: str, context: str) -> List[str]:
        """Detect issues using LLM analysis."""
        try:
            prompt = f"""
            Analyze the following AI response for potential hallucinations or inaccuracies.
            
            Context: {context}
            
            Response: {response}
            
            Look for:
            1. Information not supported by the context
            2. Overconfident statements without evidence
            3. Contradictions with the context
            4. Speculation presented as fact
            
            Provide a brief analysis of any issues found.
            """
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            analysis = completion.choices[0].message.content.strip()
            
            # Parse the analysis for issues
            issues = []
            if "issue" in analysis.lower() or "problem" in analysis.lower():
                issues.append(f"LLM detected issues: {analysis}")
            
            return issues
        
        except Exception as e:
            logger.error(f"LLM hallucination detection failed: {e}")
            return []
    
    def _calculate_confidence(self, response: str, issues: List[str]) -> float:
        """Calculate confidence in the response."""
        if not issues:
            return 1.0
        
        # Base confidence on number and severity of issues
        issue_count = len(issues)
        severity_score = sum(1 for issue in issues if "overconfidence" in issue.lower())
        
        # Calculate confidence (0.0 to 1.0)
        confidence = max(0.0, 1.0 - (issue_count * 0.2) - (severity_score * 0.3))
        
        return confidence
    
    def _generate_explanation(self, issues: List[str]) -> str:
        """Generate explanation of detected issues."""
        if not issues:
            return "No hallucination issues detected."
        
        explanation = "Potential hallucination issues detected:\n"
        for i, issue in enumerate(issues, 1):
            explanation += f"{i}. {issue}\n"
        
        return explanation
    
    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """Generate suggestions for improving the response."""
        suggestions = []
        
        if any("uncertainty" in issue.lower() for issue in issues):
            suggestions.append("Be more confident in statements that are well-supported")
        
        if any("overconfidence" in issue.lower() for issue in issues):
            suggestions.append("Add appropriate uncertainty qualifiers")
        
        if any("claim" in issue.lower() for issue in issues):
            suggestions.append("Provide evidence or sources for claims")
        
        if not suggestions:
            suggestions.append("Review response for accuracy and confidence levels")
        
        return suggestions
    
    def batch_detect(self, responses: List[str], contexts: List[str] = None) -> List[HallucinationResult]:
        """Detect hallucinations in multiple responses."""
        results = []
        
        for i, response in enumerate(responses):
            context = contexts[i] if contexts and i < len(contexts) else None
            result = self.detect_hallucination(response, context)
            results.append(result)
        
        return results
    
    def get_hallucination_stats(self, results: List[HallucinationResult]) -> Dict[str, Any]:
        """Get statistics about hallucination detection results."""
        total = len(results)
        hallucinations = sum(1 for r in results if r.is_hallucination)
        
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0.0
        
        # Count issue types
        issue_types = {}
        for result in results:
            for issue in result.detected_issues:
                issue_type = issue.split(':')[0] if ':' in issue else 'Other'
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        return {
            "total_responses": total,
            "hallucinations_detected": hallucinations,
            "hallucination_rate": hallucinations / total if total > 0 else 0.0,
            "average_confidence": avg_confidence,
            "issue_types": issue_types
        }
