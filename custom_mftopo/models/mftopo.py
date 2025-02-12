# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class custom_mftopo(models.Model):
#     _name = 'custom_mftopo.custom_mftopo'
#     _description = 'custom_mftopo.custom_mftopo'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

from odoo import models, fields, api
from odoo.exceptions import UserError

class ManufacturingOrder(models.Model):
    _inherit = 'mrp.production'

    product_ids = fields.Many2many(
        'product.product',  # The target model (products)
        'mrp_production_product_rel',  # Relation table
        'production_id',  # Field in the relation table pointing to the production
        'product_id',  # Field in the relation table pointing to the product
        string="Products",  # Label for the Many2many field
        domain=[('type', '=', 'service')],  # Optional: to filter for products only
    )     
class StockMove(models.Model):
    _inherit = 'stock.move'
        # TRING TO ADD TEH CORRECT VENDOR TO THE MF ORDER, I WANT TO FETCH IT FORM THE PURCHASE ORDER
    po_id = fields.Many2one('purchase.order', string='Purchase Order',store=True)
    vendor_id = fields.Many2one('res.partner',store=True)
    vendor_string = fields.Char(string='Vendor',store=True)


    def action_create_po(self):
        self.ensure_one()
        mrp_production = self.raw_material_production_id
        if mrp_production:
            supplier_info = self.product_id.seller_ids
            if not supplier_info:
                    # If no vendor is found for this product, you may want to raise an error or fall back to the company's default vendor
                raise UserError('No vendor found for this product.')
                
                # Get the first vendor from supplier info or you can filter by other criteria if needed
            vendor = supplier_info[0].partner_id  # 'name' refers to the partner (vendor)
            purchase_lines = [(0, 0, {
                    'product_id': self.product_id.id,
                    'product_qty': self.product_uom_qty,
                    'price_unit': self.product_id.standard_price,
                })]
            
            # Create the Purchase Order with the vendor from product's supplierinfo
            po = self.env['purchase.order'].create({
                'partner_id': vendor.id,  # Vendor from the supplier info
                'order_line': purchase_lines,
            })
            
            self.write({'po_id': po.id})
            self.write({'vendor_id': po.partner_id.id})
            
                    # Confirm the purchase order
            po.action_confirm()
                        # Return the action to open the created Purchase Order form view
            return {
                    'name': 'Create Purchase Order',
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'form',
                    'res_id': po.id,  # Pass the created PO ID to open it directly
                    'context': {
                        'default_partner_id': vendor.id,
                        'default_order_line': purchase_lines,
                    },
                }

