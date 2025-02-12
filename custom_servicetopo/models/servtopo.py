from odoo import models, fields, api
from odoo.exceptions import UserError

class ManufacturingOrder(models.Model):
    _inherit = 'mrp.production'

class ServToPo(models.Model):
    _inherit = 'product.product'

    po_id = fields.Many2one('purchase.order', string='Purchase Order')
    
    def action_create_po(self):
        for production in self:
            # Get the product for the current line (passed via context)
            product_id = self.id
            if not product_id:
                raise UserError("Product not found for creating Purchase Order.")

            product = self.env['product.product'].browse(product_id)
            
            # Ensure the product has vendor information (through seller_ids)
            if not product.seller_ids:
                raise UserError(f"No vendor found for product: {product.name}")
            
            # Choose the first vendor (or implement logic to choose the right vendor)
            vendor = product.seller_ids[0].partner_id
            purchase_lines = [(0, 0, {
                'product_id': product.id,
                'product_qty': 1,  # Quantity, adjust as necessary
                'price_unit': product.standard_price,  # The price of the product
            })]
            
            # Create the Purchase Order
            po = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'order_line': purchase_lines,
            })
            
            # Optionally, link the PO back to the Manufacturing Order
            production.write({'po_id': po.id})

            # Return the action to open the created Purchase Order form view
            return {
                'name': 'Purchase Order',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': po.id,
                'context': {
                    'default_partner_id': vendor.id,
                    'default_order_line': purchase_lines,
                },
            }
