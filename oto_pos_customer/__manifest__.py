{
    "name": "OTO Pos Customer",
    "version": "15.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Tambahan field customer POS untuk informasi kendaraan dan pengguna",
    "description": """
Tambahan field customer POS untuk mencatat data kendaraan dan pengguna kendaraan
langsung dari layar Point of Sale.
""",
    "author": "M. Kholil Lutfi S.Kom",
    "website": "",
    "depends": [
        "point_of_sale",
        "groow_otoexpert",
        "groow_contact_pks",
    ],
    "data": [
        "views/point_of_sale_assets.xml",
    ],
    "assets": {
        "web.assets_qweb": [
            "oto_pos_customer/static/src/xml/client_details_edit.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
