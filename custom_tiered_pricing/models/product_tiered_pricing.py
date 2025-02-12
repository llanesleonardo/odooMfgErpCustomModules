from odoo import api, fields, models, _, Command
import logging
_logger = logging.getLogger(__name__)

class ProductTieredPricing(models.Model):
    _inherit = 'product.template'
    _description = "Product quantity breakdown"
    _order = 'id desc'
    
    
    product_breakdown_pricing_line_ids = fields.One2many('productbreakdown.pricing.line', 'product_id', string="Pricing Lines",order='sequence')


    @api.model
    def create(self, vals):
        # Call the super method to create the product
        product = super(ProductTieredPricing, self).create(vals)
        _logger.info("product ---------------------: %s", product.read())
        # Create a pricing line with the same lst_price
        if 'list_price' in vals and vals.get('list_price', 0) >= 0:
            self.env['productbreakdown.pricing.line'].create({
                'quantity':  1.0,
                'price': vals['list_price'],
                'profit_margin': 0.0,
                'selling_price': vals['list_price'],
                'product_id': product.id,
            })
        return product
    
class ProductBreakdownPricingLine(models.Model):
    _name = 'productbreakdown.pricing.line'
    _description = "Product Breakdown Pricing Line"
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    quantity = fields.Float(string="Quantity", required=True ,default=1.0)
    price = fields.Float(string="Price", required=True)
    profit_margin = fields.Float(string="Profit Margin")
    selling_price = fields.Float(string="Selling Price",compute='_compute_selling_price', store=True)

    def _default_product(self):
        return self.env['product.template'].browse(self._context.get('active_id'))
    
    product_id = fields.Many2one('product.template', string="Product", default=_default_product, readonly=True)
    
    @api.depends('price', 'profit_margin')
    def _compute_selling_price(self):
        for record in self:
            record.selling_price = record.price * (1 + record.profit_margin / 100)

    @api.onchange('profit_margin', 'price')
    def _onchange_profit_margin(self):
        self.selling_price = self.price * (1 + self.profit_margin / 100)
        
    @api.model
    def create(self, vals):
        # Set selling_price if profit_margin and price are provided
        if 'profit_margin' in vals and 'price' in vals:
            vals['selling_price'] = vals['price'] * (1 + vals['profit_margin'] / 100)
        record = super(ProductBreakdownPricingLine, self).create(vals)
        if record.product_id:
            record._reorder_lines(record.product_id)
        return record

    def write(self, vals):
        # Update selling_price if profit_margin or price are modified
        if 'profit_margin' in vals or 'price' in vals:
            for record in self:
                profit_margin = vals.get('profit_margin', record.profit_margin)
                price = vals.get('price', record.price)
                vals['selling_price'] = price * (1 + profit_margin / 100)
        result = super(ProductBreakdownPricingLine, self).write(vals)
        if 'quantity' in vals:
            self._reorder_lines(self.mapped('product_id'))
        return result

    def _reorder_lines(self, product):
        """Sort pricing lines by quantity and update their sequence."""
        lines = self.search([('product_id', '=', product.id)]).sorted('quantity')
        for index, line in enumerate(lines, start=1):
            line.sequence = index * 10  # Persist the sequence in increments of 10