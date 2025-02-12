# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import html
import textwrap
import re
from odoo.exceptions import UserError,ValidationError

_logger = logging.getLogger(__name__)

# class .(models.Model):
#     _name = '...'
#     _description = '...'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

# This class defines a ManufacturingOrder model with fields for wrapper product, manufactured
# products, order total, customer, and logging text, along with methods to compute order total and
# product information.
class ManufacturingOrder(models.Model):
    _inherit = 'mrp.production'

    wrapper_product_id = fields.Many2one('product.product', string="Wrapper Product")
    manufactured_product_ids = fields.One2many('mrp.manufactured.product', 'mo_id', string="Manufactured Products")
    order_total = fields.Float(string="Order Total", compute='_compute_order_total',store=True)
    order_total_display = fields.Char(string="Order Total Display", compute='_compute_order_total_display')
    customer = fields.Many2one('res.partner', string="Customer", help="The responsible for this MO.")
    loggingtext = fields.Text(compute='_compute_product_info', store=True)
    loggingtext2 = fields.Text(compute='_compute_workcenter_info', store=True)
    linked_quote_id = fields.Many2one(
        'customer.quote', string="Linked Customer Quote"
    )
    @api.depends('order_total')
    def _compute_order_total_display(self):
        for record in self:
            record.order_total_display = f"$ {record.order_total:.2f}"
    
    @api.depends('manufactured_product_ids.selling_price', 'manufactured_product_ids.quantity')
    def _compute_order_total(self):
        for order in self:
            order.order_total = sum(line.selling_price * line.quantity for line in order.manufactured_product_ids)
            _logger.info(f"_compute_order_total for MO {order.id}: {order.order_total}")
            
    @api.depends('manufactured_product_ids')
    def _compute_product_info(self):
        for mo in self:
            _logger.info(f"Manufacturing Order: {mo.name}")
            
            # Get existing moves
            existing_moves = {move.id: move for move in mo.move_raw_ids}
            _logger.info(f"existing_moves {existing_moves}")
            
            new_moves = []
            moves_to_update = []
            move_ids_to_keep = set()
            
            for line in mo.manufactured_product_ids:  # EACH PRODUCT
                for material in line.product_id.estimate_ids.estimate_material_line_ids: #MANY MATERIALS
                    # Create a unique key for each material
                    production_key = f"{mo.name}_{line.id}_{line.product_id.id}_{material.product_id.id}"
                    product_related_key = f"{line.id}_{line.product_id.name}_{material.product_id.name}"
                    
                    _logger.info(f"------------------------------------------------------------")
                    _logger.info(f"production_key {production_key}")
                    _logger.info(f"product_related_key {product_related_key}")
                    _logger.info(f"------------------------------------------------------------")
                    
                    # Check if a move with the same production_key already exists
                    existing_move = next((move for move in existing_moves.values() if move.production_key == production_key), None)
                    if existing_move:
                        # Update existing move
                        moves_to_update.append((1, existing_move.id, {
                            'product_uom_qty': material.quantity * line.quantity,
                            'production_key': production_key,
                            'product_related': product_related_key,
                        }))
                        move_ids_to_keep.add(existing_move.id)
                        _logger.info(f"Updating existing move: {existing_move.id}")
                    else:
                        # Create new move
                        new_moves.append((0, 0, {
                            'product_id': material.product_id.id,
                            'product_uom_qty': material.quantity * line.quantity,
                            'product_uom': material.product_id.uom_id.id,
                            'name': material.product_id.name,
                            'location_id': mo.location_src_id.id,
                            'location_dest_id': mo.production_location_id.id,
                            'production_key': production_key,
                            'product_related': product_related_key,
                            'type_of_m': material.product_id.type
                        }))
                        _logger.info(f"Creating new move")
            
            # Identify moves to remove
            moves_to_remove = [(2, move_id) for move_id in existing_moves.keys() if move_id not in move_ids_to_keep]
            
            # Combine all operations
            all_moves = moves_to_update + new_moves + moves_to_remove
            
            _logger.info(f"Moves to update: {len(moves_to_update)}")
            _logger.info(f"New moves: {len(new_moves)}")
            _logger.info(f"Moves to remove: {len(moves_to_remove)}")
            
            # Update move_raw_ids
            if all_moves:
                mo.write({'move_raw_ids': all_moves})
            
            # Update loggingtext
            mo.loggingtext = f"Updated move_raw_ids for MO {mo.name}"

    @api.model
    def _get_last_mo_sequence(self):
        # Fetch the last manufacturing order
        last_mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        if not last_mo:
            return 'O0001'  # Default if no MO exists
        
        # Extract the numeric part of the sequence
        last_sequence = last_mo.name
        numeric_part = ''.join(filter(str.isdigit, last_sequence))
        
        # Increment the numeric part
        if numeric_part:
            next_number = int(numeric_part) + 1
            return f"O{next_number:04d}"  # Format with leading zeros
        else:
            return 'O0001'  # Fallback if no numeric part found
               
    @api.model
    def create(self, vals):
        res = super(ManufacturingOrder, self).create(vals)
        res._compute_product_info()
        res._compute_workcenter_info()
        res._compute_job_number()
        return res

    def write(self, vals):
        res = super(ManufacturingOrder, self).write(vals)
        if 'manufactured_product_ids' in vals:
            self._compute_product_info()
            self._compute_workcenter_info()
            self._compute_job_number()
        return res 
    
    
    @api.depends('manufactured_product_ids')
    def _compute_workcenter_info(self):
        for mo in self:
            _logger.info(f"Manufacturing Order: {mo.name}")

            #Collects all existing work orders (workorder_ids) associated with the manufacturing order into a dictionary, mapping their IDs to the actual records.
            #This allows quick lookup of existing work orders during processing.
            
            existing_workorders = {workorder.id: workorder for workorder in mo.workorder_ids}
            _logger.info(f"Existing Workorders: {existing_workorders}")

            #new_workorders: A list to store data for new work orders that need to be created.
            #workorders_to_update: A list to store existing work orders that need to be updated.
            #workorder_ids_to_keep: A set to track IDs of work orders that should not be deleted.

            new_workorders = []
            workorders_to_update = []
            workorder_ids_to_keep = set()

            #Iterates through each product line in manufactured_product_ids.
            #Logs each product line being processed.
            for line in mo.manufactured_product_ids:
                _logger.info(f"Processing manufactured product line: {line.product_id.name}")

                #For each product, iterates through its related work centers (work_center_ids) defined in its estimates (estimate_ids).
                #Logs the name of each work center being processed.
                if line.product_id.estimate_ids.work_center_ids:
                    for operation in line.product_id.estimate_ids.work_center_ids:
                        _logger.info(f"Processing work center: {operation.display_name}")


                        #Searches for an existing Workcenter record with a matching code (based on operation.display_name).
                        #If no matching record is found, it creates a new Workcenter with the specified name, code, and active status.
                        #Logs whether a new work center was created.
                        # Check if the work center exists by name
                        workcenter = self.env['mrp.workcenter'].search(
                            [('code', '=', operation.display_name)], limit=1
                        )
                        
                        if not workcenter:
                            _logger.info(f"Creating new work center: {operation.display_name}")
                            workcenter = self.env['mrp.workcenter'].create({
                                'name': operation.display_name,
                                'code': operation.display_name,
                                'active': True,
                            })
                            
                            
                        # Production key includes the Manufacturing Order name, product line ID, and product ID
                        production_key = f"{mo.name}_*{line.id}*_-{line.product_id.name}-_{line.product_id.id}____{workcenter.name}"
                        _logger.info(f"Production Key: {production_key}")

                        # Check for existing work order with the same production key and product_id
                        existing_workorder = next(
                        (wo for wo in mo.workorder_ids if wo.workcenter_production_product_id == production_key), None
                        )
                        _logger.info(f"Existing Workorder: {existing_workorder}")


                        # Get the product's unit of measure
                        product_uom = line.product_id.uom_id

                                    # Check if the existing work order matches the current product_id
                        if existing_workorder:
                            # Ensure the product_id matches the current product line's product_id
                            _logger.info(f"Existing Workorder: {existing_workorder.product_id.name} / { line.product_id.name}")
                            _logger.info(f"Updating existing work order: {existing_workorder.name}")
                            existing_workorder.write({
                                'workcenter_id': workcenter.id,
                                'qty_production': line.quantity,  # Make sure the quantity is correctly updated
                                'product_uom_id': product_uom.id,
                                'workcenter_production_product_id': production_key,
                                'job_number_id':line.job_number,
                            })
                            workorders_to_update.append(existing_workorder)
                            workorder_ids_to_keep.add(existing_workorder.id)
                        else:
                            _logger.info(f"Creating new work order for product: {line.product_id.name}")

                            # Ensure we are assigning the correct product_id
                            vals = {
                                'name': f"{workcenter.name}",
                                'production_id': mo.id,
                                'workcenter_id': workcenter.id,
                                'product_custom_id': line.product_id.id,  # Correctly assigning the product_id from the line
                                'job_number_id':line.job_number,
                                'qty_production': line.quantity,  # Correct quantity for the current product line
                                'product_uom_id': product_uom.id,  # Ensure the correct unit of measure is assigned
                                'workcenter_production_product_id': production_key  # Ensure the correct production key
                            }
                            new_workorder = self.env['mrp.workorder'].create(vals)
                            new_workorders.append(new_workorder.id)
                            workorder_ids_to_keep.add(new_workorder.id)
                            mo.workorder_ids |= new_workorder
            
                _logger.info(f"new_workorders {new_workorders}")
                #if new_workorders:
                #   self.env['mrp.workorder'].create(new_workorders)

            unused_workorders = mo.workorder_ids.filtered(lambda wo: wo.id not in workorder_ids_to_keep)
            unused_workorders.unlink()

            mo.loggingtext2 = f"Updated {len(new_workorders)} new and {len(workorders_to_update)} existing work orders for MO {mo.name}"
            
            
    @api.model  # No need for @api.multi in Odoo 13+
    def action_button_produce_all(self):
        # Custom logic before the original method
        for production in self:
            # Ensure there are manufactured products in the MO
            if not production.manufactured_product_ids:
                raise UserError("There are no products to manufacture in this order.")

            # Iterate over the manufactured products and create a stock picking for each one
            for line in production.manufactured_product_ids:
                product = line.product_id
                quantity = line.quantity
                _logger.info(f"product {product} - quantity {quantity}")

               
        # Call the original "Produce All" function using super() to keep its functionality
        return super(ManufacturingOrder, self).action_button_produce_all()

    @api.onchange('manufactured_product_ids')
    def onchange_job_number(self):
        _logger.info(f"manufactured_product_ids  @api.depends('manufactured_product_ids.product_id')")
        for record in self:
            c = 0
            for product in record.manufactured_product_ids:
                c += 1
               
                product.job_number = f"{record.name} - {c}"  # Use `record.name` for MO name
                

    @api.depends('manufactured_product_ids')
    def _compute_job_number(self):
        _logger.info(f"manufactured_product_ids  @api.depends('manufactured_product_ids.product_id')")
        for record in self:
            c = 0
            for product in record.manufactured_product_ids:
                c += 1
               
                product.job_number = f"{record.name} - {c}"  # Use `record.name` for MO name
                
class ManufacturedProduct(models.Model):
    _name= 'mrp.manufactured.product'
    
    mo_id = fields.Many2one('mrp.production', string="Manufacturing Order",store=True)
    job_number = fields.Char(string="Job number",store=True)
    product_id = fields.Many2one('product.product', string="Product",store=True)
    quantity = fields.Float(string="Quantity",store=True)
    selling_price = fields.Float(string="Selling price",compute="set_pricing_tiers",store=True)
    schedule_date = fields.Date(string="Schedule Date", help="Schedule date.",store=True, default= fields.Date.today())
    description = fields.Text(string="Description", help="Description.",store=True)
    selling_price_display = fields.Char(string="Selling Price", compute='_compute_selling_price_display',store=True)
    pricing_breakdown_qty = fields.Text(string="Pricing Tiers Qty", store=True)
    pricing_breakdown_prices = fields.Text(string="Pricing Tiers Selling Price",compute="set_pricing_tiers", store=True)
    sub_order_total = fields.Float(string="Sub total", compute='_compute_suborder_total',store=True)
    
    @api.onchange('product_id')
    def onchange_pricing_tiers(self):
        for record in self:
            if record.product_id:
                
                if record.mo_id.linked_quote_id:
                    for line in record.mo_id.linked_quote_id.quote_lines:
                        if line.product_id == record.product_id:
                            # Check type_of_good and set pricing_breakdown_prices
                            if record.product_id.type_of_good != 'estimate':
                                record.pricing_breakdown_qty = 1
                                record.pricing_breakdown_prices = record.product_id.list_price
                            else:
                                record.pricing_breakdown_qty = line.estimate_data_qty
                                record.pricing_breakdown_prices = line.estimate_data_pricing
                else:
                    # Fetch list price from the product
                    if record.quantity == 0:
                        record.quantity = 1
                    
                    # Fetch list price from the product
                    record.selling_price = record.product_id.list_price
            else:
                # Reset fields if no product is selected
                record.selling_price = 0.0
                record.pricing_breakdown_prices = 0.0
                record.pricing_breakdown_qty = 0
                record.pricing_breakdown_prices =  0
   
    @api.depends('product_id')
    def set_pricing_tiers(self):
        for record in self:
            if record.product_id:
                
                if record.mo_id.linked_quote_id:
                    for line in record.mo_id.linked_quote_id.quote_lines:
                        if line.product_id == record.product_id:
                            # Check type_of_good and set pricing_breakdown_prices
                            if record.product_id.type_of_good != 'estimate':
                                record.pricing_breakdown_qty = 1
                                record.pricing_breakdown_prices = record.product_id.list_price
                            else:
                                record.pricing_breakdown_qty = line.estimate_data_qty
                                record.pricing_breakdown_prices = line.estimate_data_pricing
                else:
                    # Fetch list price from the product
                    if record.quantity == 0:
                        record.quantity = 1
                    
                    # Fetch list price from the product
                    record.selling_price = record.product_id.list_price
            else:
                # Reset fields if no product is selected
                record.selling_price = 0.0
                record.pricing_breakdown_prices = 0.0
                record.pricing_breakdown_qty = 0
                record.pricing_breakdown_prices =  0
                
    @api.depends('selling_price')
    def _compute_selling_price_display(self):
        for record in self:
            record.selling_price_display = f"$ {record.selling_price:.2f}"
    
    @api.depends('selling_price','quantity')    
    def _compute_suborder_total(self):
            for record in self:
                record.sub_order_total = record.quantity * record.selling_price
            
class StockMove(models.Model):
    _inherit = 'stock.move'

    production_key = fields.Char(string="Production Key",store=True)
    product_related = fields.Char(string="Part Number",store=True)
    type_of_m = fields.Char(string="Type",store=True)
    
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    
     # Example: Adding a Char field
    workcenter_production_product_id = fields.Char(string='WorkCenter Production Product Key', help='Id')   
    product_custom_id = fields.Many2one('product.product', string="Products")
    job_number_id =  fields.Char(string='Job Number Id', help='Job Number Id')
    """
     @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            product = self.env['product.product'].browse(vals.get('product_id'))
            quantity = vals.get('quantity', 0)

            try:
                selling_price = self._compute_estimate_pline_selling_price(product, quantity)
                vals['selling_price'] = selling_price
            except UserError as e:
                self.env.user.notify_warning(message=str(e), title="Warning")

        return super(ManufacturedProduct, self).create(vals_list)
    
    
    @api.depends('quantity')
    def _onchange_product_uom_qty(self):
  
        if self.product_id and self.quantity != 0:
            try:
                self.selling_price = self._compute_estimate_pline_selling_price(
                    self.product_id, self.quantity
                )
                self.user_message1 = ""  # Clear the message
            except UserError as e:
                # Show the message as a notification
                raise ValidationError(str(e))

    def _compute_estimate_pline_selling_price(self, product, quantity):
        if not product:
            _logger.warning("No product selected.")
            return "No product selected."

        estimates = self.env['customer.estimate'].search([
            ('product_id_for_estimate_draft', '=', product.product_tmpl_id.id)
        ])
        _logger.info(f"Estimates found: {estimates}")

        if not estimates:
            return product.product_tmpl_id.list_price

        for estimate in estimates:
            if estimate.name == product.name:
                pricing_lines = estimate.estimate_pricing_line_ids

                if pricing_lines:
                    best_tier = None
                    for line in pricing_lines:
                        if line.quantity == quantity:
                            selling_price = round(line.selling_price_with_commission, 2)
                            _logger.info(f"Found exact matching pricing line: {line}")
                            return selling_price
                        elif line.quantity < quantity:
                            if best_tier is None or line.quantity > best_tier.quantity:
                                best_tier = line

                    if best_tier:
                        selling_price = round(best_tier.selling_price_with_commission, 2)
                        _logger.info(f"Found best matching pricing line: {best_tier}")
                        return selling_price
                    
                    _logger.warning(f"No suitable pricing line for quantity {quantity}.")
                    return 0
                else:
                    _logger.warning(f"No pricing lines available in estimate {estimate.name}.")
                    raise UserError("No pricing lines available.")

        _logger.error(f"No matching estimates for product {product.name}.")
        raise UserError("No estimates available for this product.")
    
    
    """