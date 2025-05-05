"""
GravitycARgo - Container Packing Optimization System
Main module exposing key components
"""

from optigenix_module.constants import CONTAINER_TYPES, TRANSPORT_MODES
from optigenix_module.models.item import Item
from optigenix_module.models.space import MaximalSpace
from optigenix_module.models.container import EnhancedContainer
from optigenix_module.optimization.genetic import optimize_packing_with_genetic_algorithm
from optigenix_module.optimization.packer import PackingGenome, GeneticPacker
from optigenix_module.optimization.temperature import TemperatureConstraintHandler
from optigenix_module.utils import get_transport_config, can_interlock

# For backward compatibility, expose all key components at the module level
__all__ = [
    'CONTAINER_TYPES',
    'TRANSPORT_MODES',
    'Item',
    'MaximalSpace',
    'EnhancedContainer',
    'PackingGenome',
    'GeneticPacker',
    'TemperatureConstraintHandler',
    'optimize_packing_with_genetic_algorithm',
    'get_transport_config',
    'can_interlock'
]

# Package initialization
from . import constants
from . import models
from .models.item import Item
from .models.container import EnhancedContainer
from .models.space import MaximalSpace
from .optimization.temperature import TemperatureConstraintHandler