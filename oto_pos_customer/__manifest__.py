{
    "name": "OTO POS Customer",
    "version": "15.0.1.2.2",
    "category": "Point of Sale",
    "summary": "Capture customer vehicle information from the POS",
    "description": """
Open a dedicated vehicle information form when creating or editing customers
from Point of Sale, then sync the selected partner back into the POS.
""",
    "author": "M. Kholil Lutfi S.Kom",
    "website": "",
    "depends": ["point_of_sale", "groow_otoexpert"],
    "data": [
        "security/ir.model.access.csv",
        "views/oto_pos_quotation_form_views.xml",
        "views/pos_order_views.xml",
        "views/point_of_sale_assets.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
