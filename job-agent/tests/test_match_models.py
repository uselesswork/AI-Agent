import pytest
from pydantic import ValidationError

from app.models.match import MatchResult


def test_match_result_requires_all_dimensions() -> None:
    with pytest.raises(ValidationError):
        MatchResult.model_validate(
            {
                "overall_score": 50,
                "recommendation": "谨慎投递",
                "summary": "信息不足",
                "dimensions": [],
            }
        )
