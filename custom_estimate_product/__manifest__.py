{
    'name': 'Custom Estimate Product',
    'version': '1.0',
    'category': 'Sales',
    'license': 'LGPL-3',
    'author':'Leonardo LLanes',
    'summary': 'Adds a custom tab to product template',
    'depends': ['base','product','customer_estimate','customer_quote'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_estimate_views.xml',
    ],
    'installable': True,
    'application': False,
}
