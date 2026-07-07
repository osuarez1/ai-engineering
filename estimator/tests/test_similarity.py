import pytest

from app.embedding_pipeline.similarity import cosine_similarity


def test_cosine_similarity_identical_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_dimension_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="same dimensionality"):
        cosine_similarity([1.0], [1.0, 0.0])


def test_cosine_similarity_zero_norm_raises() -> None:
    with pytest.raises(ValueError, match="zero-norm"):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])
