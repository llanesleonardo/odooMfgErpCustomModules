{
    'name': 'custom tiered pricing',
    'version': '1.0',
    'category': 'Sales',
    'license': 'LGPL-3',
    'summary': 'Adds a custom tab to product template',
    'depends': ['product','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}