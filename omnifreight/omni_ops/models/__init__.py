# -*- coding: utf-8 -*-

# Import mixins first so abstract models are registered
from . import mixins

# Company-level configuration the rest of the module resolves its defaults from
from . import res_company
from . import res_config_settings

from . import omni_product
from . import omni_mrp_line
from . import omni_mrp_workorder
from . import omni_bom
from . import omni_service_template
from . import omni_mrp_production
from . import omni_stock_move
from . import omni_procurement
from . import omni_stock_move_line
from . import freight_vessel
from . import freight_carrier
from . import omni_mrp_workcenter
from . import omnifreight_documents
from . import omni_hr_expense
from . import additional_file_operations
from . import account_move