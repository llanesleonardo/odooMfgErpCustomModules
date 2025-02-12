{
    'name': 'Custom Product Estimate Sales',
    'version': '1.0',
    'category': 'Sales',
    'license': 'LGPL-3',
    'author':'Leonardo LLanes',
    'summary': 'Adds a custom tab to sales order template',
    'depends': ['base','product','sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_estimate_sales_views.xml',
        'reports/report_quote_pricing_tiers.xml',
        'reports/saleorder_acknowledgement.xml',
        'reports/saleorder_jobtraveler.xml',
        'views/assets.xml',
        'views/sale_mail_template.xml',
        'views/report_views.xml'
    ],
    'installable': True,
    'application': False,
}

#        