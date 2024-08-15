"""
Golden answer test suite for evaluating workflow and agent performance.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import structlog
from ..core.workflow_engine import WorkflowEngine

logger = structlog.get_logger(__name__)


@dataclass
class GoldenTest:
    """A golden test case."""
    test_id: str
    test_type: str
    input_data: Dict[str, Any]
    expected_output: Any
    metadata: Dict[str, Any]
    tolerance: float = 0.8  # Similarity threshold


@dataclass
class TestResult:
    """Result of a golden test."""
    test_id: str
    passed: bool
    score: float
    actual_output: Any
    expected_output: Any
    error: Optional[str] = None
    execution_time_ms: int = 0


class GoldenTestSuite:
    """Suite for running golden answer tests."""
    
    def __init__(self, workflow_engine: WorkflowEngine):
        self.workflow_engine = workflow_engine
        self.tests: List[GoldenTest] = []
    
    def load_tests(self, test_file: str):
        """Load golden tests from a JSON file."""
        try:
            with open(test_file, 'r') as f:
                test_data = json.load(f)
            
            for test_case in test_data.get('tests', []):
                test = GoldenTest(
                    test_id=test_case['test_id'],
                    test_type=test_case['test_type'],
                    input_data=test_case['input_data'],
                    expected_output=test_case['expected_output'],
                    metadata=test_case.get('metadata', {}),
                    tolerance=test_case.get('tolerance', 0.8)
                )
                self.tests.append(test)
            
            logger.info(f"Loaded {len(self.tests)} golden tests from {test_file}")
        
        except Exception as e:
            logger.error(f"Failed to load golden tests: {e}")
            raise
    
    async def run_test(self, test: GoldenTest) -> TestResult:
        """Run a single golden test."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Execute the test
            if test.test_type == "workflow":
                result = await self.workflow_engine.execute_workflow(
                    workflow_id=test.metadata.get('workflow_id'),
                    input_data=test.input_data
                )
                actual_output = result.output
            elif test.test_type == "agent":
                result = await self.workflow_engine.execute_agent(
                    agent_id=test.metadata.get('agent_id'),
                    input_data=test.input_data
                )
                actual_output = result.output
            else:
                raise ValueError(f"Unknown test type: {test.test_type}")
            
            # Calculate execution time
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Evaluate the result
            score = self._calculate_similarity(actual_output, test.expected_output)
            passed = score >= test.tolerance
            
            return TestResult(
                test_id=test.test_id,
                passed=passed,
                score=score,
                actual_output=actual_output,
                expected_output=test.expected_output,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            logger.error(f"Golden test {test.test_id} failed: {e}")
            
            return TestResult(
                test_id=test.test_id,
                passed=False,
                score=0.0,
                actual_output=None,
                expected_output=test.expected_output,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all golden tests."""
        results = []
        
        for test in self.tests:
            try:
                result = await self.run_test(test)
                results.append(result)
                logger.info(f"Test {test.test_id}: {'PASSED' if result.passed else 'FAILED'} (score: {result.score:.2f})")
            except Exception as e:
                logger.error(f"Test {test.test_id} failed with error: {e}")
                results.append(TestResult(
                    test_id=test.test_id,
                    passed=False,
                    score=0.0,
                    actual_output=None,
                    expected_output=test.expected_output,
                    error=str(e)
                ))
        
        return results
    
    def _calculate_similarity(self, actual: Any, expected: Any) -> float:
        """Calculate similarity between actual and expected outputs."""
        try:
            if isinstance(actual, str) and isinstance(expected, str):
                return self._text_similarity(actual, expected)
            elif isinstance(actual, dict) and isinstance(expected, dict):
                return self._dict_similarity(actual, expected)
            elif isinstance(actual, list) and isinstance(expected, list):
                return self._list_similarity(actual, expected)
            else:
                # Exact match for other types
                return 1.0 if actual == expected else 0.0
        
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def _text_similarity(self, actual: str, expected: str) -> float:
        """Calculate text similarity using simple metrics."""
        # Simple word overlap similarity
        actual_words = set(actual.lower().split())
        expected_words = set(expected.lower().split())
        
        if not expected_words:
            return 1.0 if not actual_words else 0.0
        
        intersection = actual_words.intersection(expected_words)
        union = actual_words.union(expected_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _dict_similarity(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """Calculate dictionary similarity."""
        if not expected:
            return 1.0 if not actual else 0.0
        
        total_score = 0.0
        for key, expected_value in expected.items():
            if key in actual:
                key_score = self._calculate_similarity(actual[key], expected_value)
                total_score += key_score
            else:
                total_score += 0.0
        
        return total_score / len(expected)
    
    def _list_similarity(self, actual: List[Any], expected: List[Any]) -> float:
        """Calculate list similarity."""
        if not expected:
            return 1.0 if not actual else 0.0
        
        if len(actual) != len(expected):
            return 0.0
        
        total_score = 0.0
        for actual_item, expected_item in zip(actual, expected):
            item_score = self._calculate_similarity(actual_item, expected_item)
            total_score += item_score
        
        return total_score / len(expected)
    
    def get_test_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Get a summary of test results."""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests
        
        avg_score = sum(r.score for r in results) / total_tests if total_tests > 0 else 0.0
        avg_execution_time = sum(r.execution_time_ms for r in results) / total_tests if total_tests > 0 else 0.0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "average_score": avg_score,
            "average_execution_time_ms": avg_execution_time,
            "results": [
                {
                    "test_id": r.test_id,
                    "passed": r.passed,
                    "score": r.score,
                    "execution_time_ms": r.execution_time_ms,
                    "error": r.error
                }
                for r in results
            ]
        }
    
    def save_results(self, results: List[TestResult], output_file: str):
        """Save test results to a file."""
        try:
            summary = self.get_test_summary(results)
            
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Saved test results to {output_file}")
        
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
            raise
