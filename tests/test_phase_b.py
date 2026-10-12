"""Student logic uses mock SDK; never invokes the live judge."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src import phase_b_judge as phase

pytestmark = pytest.mark.student
Q,A,B,REF = "Q", "Correct detailed answer", "Wrong", "Policy reference"


def test_pairwise_uses_json_judge(openai_client):
    result = phase.pairwise_judge(Q,A,B,reference=REF)
    assert result == {"winner":"A","reasoning":"Matches the supplied policy.","scores":{"A":.9,"B":.2}}
    openai_client.chat.completions.create.assert_called_once()
    call = openai_client.chat.completions.create.call_args.kwargs
    assert REF in str(call["messages"])
    assert call["response_format"] == {"type":"json_object"}


@pytest.mark.parametrize("scores", [
    {"scores": {"a": 0.8, "b": 0.6}},
    {"scores_a": 0.8, "scores_b": 0.6},
    {"score_a": 0.8, "score_b": 0.6},
])
def test_pairwise_normalizes_observed_gemini_score_shapes(openai_client, scores):
    payload = {"winner": "a", "reasoning": "A covers the essential condition.", **scores}
    openai_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    result = phase.pairwise_judge(Q, A, B, reference=REF)
    assert result["winner"] == "A"
    assert result["scores"] == {"A": 0.8, "B": 0.6}


@pytest.mark.parametrize("second_raw,expected,consistent", [("B","A",True),("A","tie",False)])
def test_swap_conversion_and_calls(monkeypatch,second_raw,expected,consistent):
    mocked = Mock(side_effect=[
        {"winner":"A","reasoning":"first","scores":{"A":.9,"B":.2}},
        {"winner":second_raw,"reasoning":"second","scores":{"A":.2,"B":.9}}])
    monkeypatch.setattr(phase,"pairwise_judge",mocked)
    result = phase.swap_and_average(Q,A,B,reference=REF)
    assert mocked.call_count == 2
    assert mocked.call_args_list[0].args[:3] == (Q,A,B)
    assert mocked.call_args_list[1].args[:3] == (Q,B,A)
    assert result.winner_pass2 == ("A" if second_raw=="B" else "B")
    assert result.final_winner == expected and result.position_consistent is consistent
    assert result.scores_pass2 == {"A":.9,"B":.2}


@pytest.mark.parametrize("judge,human,expected", [
    ([1,0,1,0],[1,0,1,0],1), ([1,0,1,0],[0,1,0,1],-1),
    ([1,1,0,0],[1,0,1,0],0)])
def test_kappa_exact(judge,human,expected):
    assert phase.cohen_kappa(judge,human) == pytest.approx(expected)


def test_bias_known_counts():
    rows = [
        phase.JudgeResult(Q,A,B,"A","A","A","r1","r2",True),
        phase.JudgeResult(Q,A,B,"A","B","tie","r1","r2",False)]
    result = phase.bias_report(rows)
    assert result["total_judged"] == 2 and result["position_bias_count"] == 1
    assert result["position_bias_rate"] == .5 and result["verbosity_bias"] == 1
    assert result["interpretation"].strip()


def test_bias_empty():
    assert phase.bias_report([])["total_judged"] == 0
