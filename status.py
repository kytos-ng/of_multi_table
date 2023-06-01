"""Defined status for pipeline"""
from enum import Enum


class PipelineStatus(Enum):
    """Enum for pipeline status"""

    ENABLED = "enabled"
    ENABLING = "enabling"
    ENABLING_ERROR = "enabling_error"
    DISABLED = "disabled"
    DISABLING = "disabling"
    DISABLING_ERROR = "disabling_error"
