"""Tenant-isolated illustrative fixtures for demo mode."""

from __future__ import annotations

from logsentinel.ui.fixtures.bgl import get_bgl_demo_data
from logsentinel.ui.fixtures.hdfs import get_hdfs_demo_data

__all__ = ["get_bgl_demo_data", "get_hdfs_demo_data"]
