# -*- coding: utf-8 -*-
{
    'name': "customer_multiple_mo",

    'summary': " Multiple manufactured products using 1 MO",

    'description': """
            Multiple manufactured products using 1 MO
    """,

    'author': "Special Carbide Tools Inc",
    'website': "https://www.specialcarbide.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacture',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','customer_quote','purchase','mrp','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'reports/report_acknowledgement.xml',
        'reports/report_jobtraveler.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

