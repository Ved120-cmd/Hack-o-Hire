"""
Cryptographic hashing utilities for data integrity and audit trails
Implements SHA-256 hashing for various data structures
"""

import hashlib
import json
from typing import Any, Dict, List


def compute_sha256(data: str) -> str:
    """
    Compute SHA-256 hash of string data

    Args:
        data: String data to hash

    Returns:
        Hexadecimal SHA-256 hash string (64 characters)
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_dict_hash(data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of dictionary data

    Args:
        data: Dictionary to hash

    Returns:
        Hexadecimal SHA-256 hash string

    Note:
        Dictionary is serialized to JSON with sorted keys for consistent hashing
    """
    json_str = json.dumps(data, sort_keys=True, default=str)
    return compute_sha256(json_str)


def compute_list_hash(data: List[Any]) -> str:
    """
    Compute SHA-256 hash of list data

    Args:
        data: List to hash

    Returns:
        Hexadecimal SHA-256 hash string
    """
    json_str = json.dumps(data, default=str)
    return compute_sha256(json_str)


def compute_pipeline_chain_hash(transforms: List[Dict[str, Any]]) -> str:
    """
    Compute cumulative hash of pipeline transforms

    Args:
        transforms: List of transform dictionaries with 'hash' keys

    Returns:
        Cumulative SHA-256 hash representing entire pipeline chain

    Note:
        Creates a chain hash by combining all transform hashes in sequence
    """
    if not transforms:
        return compute_sha256("")

    chain = "".join([t.get("hash", "") for t in transforms])
    return compute_sha256(chain)


def compute_data_lineage_hash(
    case_id: str, alert_ids: List[str], customer_data: Dict[str, Any]
) -> str:
    """
    Compute data lineage hash for audit trail

    Args:
        case_id: Case identifier
        alert_ids: List of alert identifiers
        customer_data: Customer data dictionary

    Returns:
        SHA-256 hash representing data lineage
    """
    lineage_components = {
        "case_id": case_id,
        "alert_ids": sorted(alert_ids),
        "customer_hash": compute_dict_hash(customer_data),
    }
    return compute_dict_hash(lineage_components)


def compute_claim_input_hash(
    case_id: str,
    alert_ids: List[str],
    customer_data: Dict[str, Any],
    rule_results: Dict[str, Any],
    fraud_scores: Dict[str, Any],
) -> str:
    """
    Compute comprehensive input hash for claim generation

    Args:
        case_id: Case identifier
        alert_ids: Alert identifiers
        customer_data: Customer data
        rule_results: Rule engine results
        fraud_scores: Fraud model scores

    Returns:
        SHA-256 hash of all input data
    """
    input_components = {
        "case_id": case_id,
        "alert_ids": sorted(alert_ids),
        "customer_hash": compute_dict_hash(customer_data),
        "rules_hash": compute_dict_hash(rule_results),
        "fraud_hash": compute_dict_hash(fraud_scores),
    }
    return compute_dict_hash(input_components)


def compute_claim_output_hash(claim_object: Dict[str, Any]) -> str:
    """
    Compute output hash of generated claim object

    Args:
        claim_object: Complete claim object dictionary

    Returns:
        SHA-256 hash of claim object

    Note:
        Excludes integrity_hashes field to avoid circular dependency
    """
    claim_copy = claim_object.copy()
    claim_copy.pop("integrity_hashes", None)
    return compute_dict_hash(claim_copy)


def compute_full_chain_hash(input_hash: str, output_hash: str, pipeline_hash: str) -> str:
    """
    Compute full chain hash combining input, output, and pipeline

    Args:
        input_hash: Input data hash
        output_hash: Output claim hash
        pipeline_hash: Pipeline transforms hash

    Returns:
        Combined SHA-256 hash of entire processing chain
    """
    chain_data = f"{input_hash}{output_hash}{pipeline_hash}"
    return compute_sha256(chain_data)


def verify_hash_integrity(data: str, expected_hash: str) -> bool:
    """
    Verify data integrity against expected hash

    Args:
        data: Data to verify
        expected_hash: Expected SHA-256 hash

    Returns:
        True if hashes match, False otherwise
    """
    computed_hash = compute_sha256(data)
    return computed_hash == expected_hash


def verify_dict_integrity(data: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify dictionary integrity against expected hash

    Args:
        data: Dictionary to verify
        expected_hash: Expected SHA-256 hash

    Returns:
        True if hashes match, False otherwise
    """
    computed_hash = compute_dict_hash(data)
    return computed_hash == expected_hash