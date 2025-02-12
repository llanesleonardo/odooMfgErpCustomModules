from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class PoMoAssigment(models.Model):
    _inherit = 'purchase.order'

    manufacturing_order_ids = fields.Many2many('mrp.production', string='Manufacturing Orders')
    mo_count = fields.Integer(compute='_compute_mo_count', string='MO Count')
    show_po_products = fields.Boolean(string="Show PO Products", default=False)
    purchased_products_array = fields.Char(string="Array of Objects", default='[]')
    product_to_split_ids = fields.One2many('split.po.line', 'po_id_to_split', string="Splited MOs")
    product_domain = fields.Many2many('product.product', compute='_compute_product_domain')


    
    def get_array_field(self):
        return json.loads(self.purchased_products_array)

    def set_array_field(self, value):
       self.purchased_products_array = json.dumps(value)
        
    def toggle_po_products(self):
        self.show_po_products = not self.show_po_products
        if self.show_po_products:
            self.get_po_product()
        else:
            self.product_to_split_ids.unlink()

    
    @api.depends('manufacturing_order_ids')
    def _compute_mo_count(self):
        for order in self:
            order.mo_count = len(order.manufacturing_order_ids)
            
    def action_view_mo(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        action['domain'] = [('id', 'in', self.manufacturing_order_ids.ids)]
        return action


    @api.model
    def get_po_product(self):
        purchased_products = {}
        for line in self.order_line:
            purchased_products[line.product_id.id] = line.product_qty
                
        _logger.info(f"purchased_products: {purchased_products}")
        if purchased_products:
            self.set_array_field(purchased_products)   
            
        # You can call this method to update the array_field
    def update_po_products(self):
        for order in self:
            order.get_po_product()
    
    """        
    def check_and_update_manufacturing_orders(self):
            for order in self:
                # If no Manufacturing Orders, raise exception
                if not order.manufacturing_order_ids:
                    raise UserError("No Manufacturing Orders assigned. All products will go to stock.")
                
                # Get purchased products and their quantities
                purchased_products = {}
                for line in self.order_line:
                    purchased_products[line.product_id.id] = line.product_qty
                
                _logger.info(f"purchased_products: {purchased_products}")
                if purchased_products:
                    self.set_array_field(purchased_products)    
                # Process each Manufacturing Order
                for mo in order.manufacturing_order_ids.move_raw_ids:
                    # Check if MO product exists in purchased products
                    if mo.product_id not in purchased_products:
                        raise ValidationError(f"Manufacturing Order Product {mo.product_id.name} not found in Purchase Order")
                    

                # Optional: Additional logging or confirmation
                self.message_post(body="Manufacturing Orders verified and updated successfully")
    """
    @api.depends('order_line.product_id')
    def _compute_product_domain(self):
        for order in self:
            order.product_domain = order.order_line.mapped('product_id')               

    total_split_quantity = fields.Float(string='Total Split Quantity', compute='_compute_total_split_quantity', store=True)

    @api.depends('product_to_split_ids.product_id_to_split_quantity')
    def _compute_total_split_quantity(self):
        for order in self:
            order.total_split_quantity = sum(order.product_to_split_ids.mapped('product_id_to_split_quantity'))
    
    total_product_qty = fields.Float(string='Total Product Quantity', compute='_compute_total_product_qty', store=True)

    @api.depends('order_line.product_qty')
    def _compute_total_product_qty(self):
        for order in self:
            order.total_product_qty = sum(order.order_line.mapped('product_qty'))

    @api.onchange('total_product_qty', 'total_split_quantity')
    def _onchange_check_split_quantity(self):
        for order in self:
            if order.total_split_quantity > order.total_product_qty:
                return {
                    'warning': {
                        'title': 'Invalid Split Quantity',
                        'message': "Total split quantity cannot exceed total product quantity."
                    }
                }
                
    @api.constrains('total_product_qty', 'total_split_quantity')
    def _check_split_quantity(self):
        for order in self:
            if order.total_split_quantity > order.total_product_qty:
                raise ValidationError("Total split quantity cannot exceed total product quantity.")

    split_quantity_valid = fields.Boolean(compute='_compute_split_quantity_valid', store=True)

    @api.depends('total_product_qty', 'total_split_quantity')
    def _compute_split_quantity_valid(self):
        for order in self:
            order.split_quantity_valid = order.total_split_quantity <= order.total_product_qty


class SplitPoLines(models.Model):
    _name = 'split.po.line'
    _description = "Split PO Line"
    #split_line_ids = fields.One2many('split.po.line', 'po_id_to_split', string="Split Lines", store=True)
    product_id_to_split = fields.Many2one('product.product', string='Product', domain="[('id', 'in', parent.product_domain)]", store=True)
    po_id_to_split = fields.Many2one('purchase.order', string="Purchase Order",store=True)
    manufacturing_order_id = fields.Many2one(
        'mrp.production', 
        string='Manufacturing Order',
        help='Related Manufacturing Order for this Purchase Order Line',
        store=True
    )
    
    product_id_to_split_quantity = fields.Float(string='Quantity To Consume', required=True, store=True)
       
    #def _get_purchased_products(self):
     #return [(str(line.product_id.id), f"{line.product_id.name}: {line.product_qty}") for line in self.po_id_to_split.order_line]
    
    @api.onchange('po_id_to_split')
    def _onchange_po_id_to_split(self):
        if self.po_id_to_split:
            return {'domain': {'product_id_to_split': [('id', 'in', self.po_id_to_split.order_line.mapped('product_id').ids)]}}
        return {'domain': {'product_id_to_split': []}}
    
    
    @api.depends('manufacturing_order_id')
    def _compute_filtered_mo_lines(self):
        for record in self:
            if record.manufacturing_order_id:
                    record.filtered_mo_lines = record.manufacturing_order_id.move_raw_ids.filtered(
                    lambda line: line.product_id == record.product_id_to_split
                )
            else:
                record.mo_lines = False
                
    filtered_mo_lines = fields.One2many('stock.move', string='Filtered MO Lines', compute='_compute_filtered_mo_lines')
    
    @api.depends('filtered_mo_lines')
    def _compute_mo_lines_quantity(self):
        for record in self:
            record.mo_lines_quantity = sum(record.filtered_mo_lines.mapped('product_uom_qty'))

    mo_lines_quantity = fields.Float(string='MO Product Qty Line', compute='_compute_mo_lines_quantity')
    
    @api.onchange('manufacturing_order_id', 'product_id_to_split')
    def _onchange_filtered_mo_lines(self):
        if self.manufacturing_order_id and self.product_id_to_split:
            self.filtered_mo_lines = self.manufacturing_order_id.move_raw_ids.filtered(
                lambda line: line.product_id == self.product_id_to_split
            )
        else:
            self.filtered_mo_lines = False
        
        self._onchange_mo_lines_quantity()

    @api.onchange('filtered_mo_lines')
    def _onchange_mo_lines_quantity(self):
        self.mo_lines_quantity = sum(self.filtered_mo_lines.mapped('product_uom_qty'))