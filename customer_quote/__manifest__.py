# -*- coding: utf-8 -*-
{
    'name': "customer_quote",

    'summary': "Custom Quote  Module",

    'description': """
                Custom Quote  Module
    """,

    'author': "Special Carbide Tools Inc",
    'website': "https://www.specialcarbide.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mrp','web','sale','crm','product','customer_estimate'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/quote_pricing_tiers.xml',
        'views/views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': False,
}

