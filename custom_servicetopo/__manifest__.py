# -*- coding: utf-8 -*-
{
    'name': "custom_servtopo",

    'summary': "Connection between SERV and PO",

    'description': """
Connection between SERV and PO
    """,

    'author': "Special Carbide Tools",
    'website': "https://www.specialcarbide.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacturing',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','purchase','mrp','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/servtopo.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

