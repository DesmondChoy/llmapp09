"""
Shared fixtures and configuration for deepeval LLM evaluation tests.
"""

import pytest
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from judge import get_judge


# ---------------------------------------------------------------------------
# Reusable GEval metric factories
# ---------------------------------------------------------------------------

def json_schema_metric(schema_description: str):
    """Creates a GEval metric that checks JSON schema compliance."""
    return GEval(
        model=get_judge(),
        name="JSON Schema Compliance",
        criteria=(
            "Evaluate whether the actual output is valid JSON that conforms to "
            "the required schema. Only check structure, key names, and data "
            "types — do NOT penalize for specific values. "
            + schema_description
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,
    )


def output_correctness_metric():
    """Creates a GEval metric that checks factual/logical correctness."""
    return GEval(
        model=get_judge(),
        name="Output Correctness",
        criteria=(
            "Determine whether the actual output is logically correct and "
            "reasonable given the input text. The analysis should make sense "
            "for the provided input."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,
    )


def answer_relevancy_metric():
    """Creates a GEval metric that checks whether the output is topically
    relevant to the input.  Unlike AnswerRelevancyMetric (which assumes a
    Q&A format), this works for classification and analysis endpoints where
    the output is structured metadata about the input text."""
    return GEval(
        model=get_judge(),
        name="Answer Relevancy",
        criteria=(
            "Evaluate whether the actual output is topically relevant to the "
            "input text. The labels, categories, or analysis in the output "
            "should directly relate to the subject matter of the input. "
            "Structured metadata (labels, categories, confidence scores) that "
            "accurately describes the input text should be considered relevant."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,
    )


def sentiment_relevancy_metric():
    """Judge relevance to the sentiment task, including neutral inputs."""
    return GEval(
        model=get_judge(),
        name="Sentiment Relevancy",
        evaluation_steps=[
            "Read the input text and identify its emotional tone, including "
            "the possibility that it expresses no emotion.",
            "Check whether the output provides sentiment analysis of that "
            "input through overallSentiment, sentimentScore, and emotions.",
            "A neutral label, a score near zero, and an empty emotions list "
            "are relevant for factual or logistical input. The output does "
            "not need to repeat names, places, events, or other topic details.",
            "Give a low relevance score to output that performs another task, "
            "discusses unrelated content, or invents emotional context "
            "unsupported by the input. A sentiment label alone does not "
            "make an otherwise unrelated response relevant.",
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,
    )
