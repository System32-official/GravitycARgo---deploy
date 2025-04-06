"""
Package initialization file for optigenix_module.utils
"""
# This file makes the 'utils' directory a proper Python package
# so it can be imported using: from optigenix_module.utils import llm_connector

# Import utility functions to expose them at the package level
from optigenix_module.utils.common import get_transport_config, can_interlock