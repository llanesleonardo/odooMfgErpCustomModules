# -*- coding: utf-8 -*-
{
    'name': 'Customer Estimate',
    'version': '18.0',
    'category': 'Sales',
    'summary': 'Custom module to customer estimate management',
    'description': '',
    'depends': ['base','web','sale','sale_stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/estimate.xml',
        'views/workcenter_template.xml',
        'views/assets.xml',
        'reports/report_estimate.xml'
    ],
    'author': '',
    'company': '',
    'website': '',
    'license': 'LGPL-3',
    'images': [],
    'demo': [],
        'assets': {
            'web.layout': [
                'customer_estimate/static/src/js/qty_at_date_widget.js',
                'customer_estimate/static/src/xml/qty_at_date_widget.xml',
            ],
        },
    'installable': True,
    'application': False,
}
