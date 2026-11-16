"""Small, auditable cleaning pipeline for a synthetic support-ticket dataset."""

from .cleaning import PipelineError, PipelineResult, clean, inspect, load_csv

__all__ = ["PipelineError", "PipelineResult", "clean", "inspect", "load_csv"]
