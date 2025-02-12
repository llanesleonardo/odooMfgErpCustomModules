from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manufacturing_order_id = fields.Many2one('mrp.production', string='Manufacturing Order')

    def create_manufacturing_order(self):
        mo_count = 0
        for order in self:
            for line in order.order_line:
                product = line.product_id

                # Check if the product has an associated estimate
                if product.product_tmpl_id.estimate_ids:

                    estimate = product.product_tmpl_id.estimate_ids
                    _logger.info(f"PRODUCT BOM IDS: {product.bom_ids.bom_line_ids.read()}")
                    # Check if the product has a BOM
                    if not product.bom_ids:
                        # Ensure no cyclic BOM creation
                        bom_vals = {
                            'product_tmpl_id': product.product_tmpl_id.id,
                            'type': 'normal',
                            'product_qty': 1.0,
                            'bom_line_ids': [
                                (0, 0, {
                                    'product_id': component.product_id.id,
                                })
                                for component in estimate.estimate_material_line_ids
                                if component.product_id.type != 'service'  # Only stockable products
                            ],
                            'operation_ids': [],
                        }

                        # Add operations and work centers
                        for operation in estimate.work_center_ids:
                            workcenter = self.env['mrp.workcenter'].search([('code', '=', operation.display_name)], limit=1)
                            if not workcenter:
                                # If the work center doesn't exist, create it
                                workcenter = self.env['mrp.workcenter'].create({
                                    'name': operation.display_name,
                                    'code': operation.display_name,
                                    'active': True,                                })

                            # Add the operation to the BOM
                            bom_vals['operation_ids'].append((0, 0, {
                                'name': operation.display_name,
                                'workcenter_id': workcenter.id
                            }))

                        # Create the BOM with the added operations
                        bom = self.env['mrp.bom'].create(bom_vals)

                    # Use the first BOM available
                    bom = product.bom_ids[0]

                    # Verify the BOM is valid and does not include the product itself
                    for bom_line in bom.bom_line_ids:
                        if bom_line.product_id == product:
                            raise UserError(f"Invalid BOM configuration: '{product.name}' cannot be a component of its own BOM.")

                    # Initialize an empty list to store product IDs (including services)
                    product_idsA = []
                    po_prod = []
                    # Add services
                    for component in estimate.estimate_material_line_ids:
                        if component:
                            po_prod.append({
                                    'prod': component.product_id.id,  # Use appropriate attribute for the product ID
                                    'po': component.rfc_po_id             # Use appropriate attribute for the PO ID
                            })
                        
                        if component.product_id.type == 'service':  # Only services
                            product_idsA.append(component.product_id.id)
                            
                            
                    _logger.info(f"PO ARRAYYYYYYYYYYYYYYY        ---> {po_prod}")
                    # Proceed to create a Manufacturing Order
                    vals = {
                        'product_id': product.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom_id': line.product_uom.id,
                        #'bom_id': bom.id,
                        'origin': order.name,
                        'company_id': order.company_id.id,
                        'product_ids': [(6, 0, product_idsA)],  # Many2many field for products (using the correct format for Many2many)

                    }

                   
                    mo = self.env['mrp.production'].create(vals)
                    _logger.info(f"Manufacturing Order created: {mo.move_raw_ids.read()}")
                    order.manufacturing_order_id = mo.id
                    mo_count += 1
                    
                    # Assuming 'mo' is your manufacturing order object
                    for bom_line in bom.bom_line_ids:
                        # Check if a move already exists for this product
                        existing_move = mo.move_raw_ids.filtered(lambda m: m.product_id.id == bom_line.product_id.id)
                        _logger.info(f"Existing move for {bom_line.product_id.name}: {existing_move.read() if existing_move else 'None'}")
                        matching_po = None
                        if not existing_move:
                            # If no move exists, create a new one
                            matching_po = next((item['po'] for item in po_prod if item['prod'] == bom_line.product_id.id), None)
                            move_vals = {
                                'product_id': bom_line.product_id.id,
                                'product_uom_qty': bom_line.product_qty * mo.product_qty,
                                'product_uom': bom_line.product_uom_id.id,
                                'production_id': mo.id,
                                'location_id': mo.location_src_id.id,
                                'location_dest_id': mo.production_location_id.id,
                                'name': f"{mo.name}: {bom_line.product_id.name}",
                            }
                            _logger.info(f"Matching PO for NOT existing_move {bom_line.product_id.name}: {matching_po.read()}")
                            # Find matching PO if it exists
                            if matching_po:
                                move_vals.update({
                                    'po_id': matching_po.id,
                                    'vendor_id': matching_po.partner_id
                                })
                            
                            # Create the new move and add it to move_raw_ids
                            new_move = self.env['stock.move'].create(move_vals)
                            mo.write({'move_raw_ids': [(4, new_move.id)]})
                            
                            _logger.info(f"Created new move for  {bom_line.product_id.name}: {new_move.po_id}")
                        else:
                                                        # If a move already exists, update it if necessary
                            _logger.info(f"po_prod {po_prod}")
                            matching_po = next((item['po'] for item in po_prod if item['prod'] == bom_line.product_id.id), None)
                            _logger.info(f"Matching PO for existing_move {bom_line.product_id.name}: {matching_po.read()}")
                            if matching_po:
                                
                                existing_move.write({
                                    'po_id': matching_po.id,
                                    'vendor_id': matching_po.partner_id.id
                                })
                            _logger.info(f"Updated existing move for {bom_line.product_id.name}: {existing_move.vendor_id.read()}")

                    # After processing all BOM lines, you might want to remove any extra moves
                    extra_moves = mo.move_raw_ids.filtered(lambda m: m.product_id not in bom.bom_line_ids.mapped('product_id'))
                    if extra_moves:
                        mo.write({'move_raw_ids': [(2, move.id) for move in extra_moves]})
                        _logger.info(f"Removed extra moves: {extra_moves.mapped('product_id.name')}")

                   
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': self.env.ref('sale.sale_menu_root').id,
                'action': self.env.ref('sale.action_orders').id,
                'id': self.id,
            },
            'target': 'current',
            'notify': {
                'title': 'Success',
                'message': f'{mo_count} Manufacturing Orders created successfully',
                'sticky': False,
            },
        }
        
        
        
        """
         # Manually add the BOM lines to the Manufacturing Order if they aren't added automatically
                    for bom_line in bom.bom_line_ids:
                        existing_line = self.env['stock.move'].search([
                            ('production_id', '=', mo.id),
                            ('product_id', '=', bom_line.product_id.id)
                        ], limit=1)
                        
                        _logger.info(f"BOM PRODUCT Checking if product {bom_line.product_id.name} exists in Manufacturing Order {mo.name}")
                        
                        if not existing_line:
                            matching_po = next((item['po'] for item in po_prod if item['prod'] == bom_line.product_id.id), None)
                            _logger.info(f"matching_po {matching_po.read() if matching_po else 'None'} ")
                            
                            smove_vals = {
                                'production_id': mo.id,
                                'product_id': bom_line.product_id.id,
                            }
                            
                            if matching_po:
                                smove_vals.update({
                                    'po_id': matching_po.id,
                                    'vendor_id': matching_po.partner_id.id
                                })
                            
                            smove = self.env['stock.move'].create(smove_vals)
                            _logger.info(f"Created stock move: {smove.read()} ")
        
        """