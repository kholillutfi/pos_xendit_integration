{
    "name": "OTO POS Customer",
    "version": "15.0.1.2.7",
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
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/oto_pos_quotation_form_views.xml",
        "views/pos_order_views.xml",
        "views/point_of_sale_assets.xml",
        "report/pos_invoice_58_report.xml",
        "report/pos_invoice_58_template.xml",
    ],
    "assets": {
        "web.assets_qweb": [
            "oto_pos_customer/static/src/xml/order_receipt.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
