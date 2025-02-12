from odoo import api, fields, models, _

class ProductEstimateTemplate(models.Model):
    _inherit = 'product.template'
    _order = 'id desc'
    
    quote_ids = fields.Many2many('customer.quote',string="Related Quotes")
    estimate_ids = fields.One2many('customer.estimate','product_id_for_estimate_draft', string='Estimate')
    #THE FIELD BELOW IS NOT WORKING, IT IS DEPRECATED
    #estimatex_id = fields.One2many('customer.estimate','product_id_for_estimate_draft', string='Estimatessssssaaaaa', deprecated=True)
    type_of_good = fields.Selection([('prod', 'Product'), ('service', 'Service'), ('estimate', 'Estimate')], string='Type of Good', default='prod', store=True)
    warehouse_location = fields.Char(string="Warehouse", compute="_compute_location_fields",store=True)
    lot_location = fields.Char(string="Lot", compute="_compute_location_fields",store=True)
    bin_location = fields.Char(string="Bin", compute="_compute_location_fields",store=True)
    stock_quant_ids = fields.One2many(related='product_variant_ids.stock_quant_ids')
    
    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'deprecated' or super()._valid_field_parameter(field, name)
    
     
    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'deprecated' or super()._valid_field_parameter(field, name)
    
    @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids')
    def _compute_location_fields(self):
        for template in self:
            variant = template.product_variant_ids[:1]  # Get the first variant
            if variant:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', variant.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                
                if quant:
                    location = quant.location_id
                    location_hierarchy = []
                    while location:
                        location_hierarchy.insert(0, location.name)
                        location = location.location_id
                    
                    # Join the first two elements (WH/STOCK) if they exist
                    if len(location_hierarchy) >= 3:
                        template.warehouse_location = '/'.join(location_hierarchy[:3])
                    else:
                        template.warehouse_location = location_hierarchy[0] if location_hierarchy else ''
                    
                    # Extract LOT (3rd element if it exists)
                    template.lot_location = location_hierarchy[3] if len(location_hierarchy) > 3 else ''
                    
                    # Join the rest as BIN (4th element onwards)
                    template.bin_location = '/'.join(location_hierarchy[4:]) if len(location_hierarchy) > 4 else ''
                else:
                    template.warehouse_location = template.lot_location = template.bin_location = ''
            else:
                template.warehouse_location = template.lot_location = template.bin_location = ''

