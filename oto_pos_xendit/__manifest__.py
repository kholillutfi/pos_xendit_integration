# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "OTO Pos Xendit",
    "version": "15.0.1.0",
    "category": "Point of Sale",
    "summary": "Add Xendit as a Point of Sale payment terminal option",
    "description": """
Integrasi Xendit QRIS untuk Point of Sale Odoo, lengkap dengan konfigurasi
payment terminal, request QRIS, pencatatan transaksi, status transaksi, dan
webhook.
""",
    "author": "M. Kholil Lutfi S.Kom",
    "website": "",
    "depends": ["base", "web", "point_of_sale"],
    "data": [
        "data/ir_sequence_data.xml",
        "security/oto_pos_xendit_security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/pos_payment_xendit_config_views.xml",
        "views/pos_payment_xendit_transaction_views.xml",
        "views/pos_payment_xendit_webhook_views.xml",
        "views/pos_payment_method_views.xml",
        "views/point_of_sale_assets.xml",
    ],
    "assets": {
        "web.assets_qweb": [
            "oto_pos_xendit/static/src/xml/payment_xendit.xml",
        ],
    },
    "installable": True,
    "license": "OPL-1",
    "auto_install": False,
}
