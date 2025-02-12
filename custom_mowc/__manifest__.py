# -*- coding: utf-8 -*-
{
    'name': "custom_mowc",

    'summary': "",

    'description': """

    """,

    'author': "Special Carbide Tools",
    'website': "https://www.specialcarbide.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mrp','resource'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'demo/demo.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

