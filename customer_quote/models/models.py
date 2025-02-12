# -*- coding: utf-8 -*-

# from odoo import models, fields, api


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

# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo import fields


import logging
import html
import textwrap
import re
from odoo.exceptions import UserError,ValidationError

_logger = logging.getLogger(__name__)

class CustomerQuote(models.Model):
    _name = 'customer.quote'
    _description = "Customer Quote"

    name = fields.Char(string="Name", required=True)
    customer_id = fields.Many2one('res.partner', string="Customer", required=True, help="The customer associated with this quote.")
    expiration_date = fields.Date(string="Expiration Date", help="The date until which the quote is valid.")
    quote_date = fields.Date(string="Quote Date", default=fields.Date.today, help="The date when the quote was created.")
    payment_terms = fields.Text(string="Payment Terms", help="Terms and conditions for payment.")
    sales_team_user_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user, help="The salesperson responsible for this quote.")
    sales_team = fields.Many2one('crm.team', string="Sales Team", help="The sales team associated with this quote.")
    sign_by = fields.Char(string="Signed By", help="The person who signed the quote.")
    commitment_date = fields.Date(string="Commitment Date", help="Delivery date.")
    note = fields.Text(string="Notes", help="Qoute Notes.")
    lock_fields = fields.Boolean(string="Lock fields",store=True)
      # One2many relationship to CustomerQuoteLines
    quote_lines = fields.One2many('customer.quote.lines', 'quote_id', string="Quote Lines", help="The lines associated with this quote.")
    quote_status = fields.Selection([('draft', 'Draft'), ('review', 'Review'), ('confirmed', 'Confirmed')], string='Status',  store=True,help="Quote status.", default='draft')
    product_quote_ids = fields.Many2many('product.template', string="Related Products",required=False)
    def action_review(self):
        """Change status to Review."""
        self.write({'quote_status': 'review'})

    def action_confirm(self):
        """Change status to Confirmed."""
        self.write({'quote_status': 'confirmed'})
    
    @api.model
    def create(self, vals):
        _logger.info("Starting creation of CustomerQuote")
        _logger.debug("Received vals: %s", vals)

        # Create the quote as usual
        quote = super(CustomerQuote, self).create(vals)
        _logger.info("Quote created with ID: %s", quote.id)

        # Collect product IDs from quote lines
        product_ids = set()
        if 'quote_lines' in vals:
            for line in vals['quote_lines']:
                if line[0] == 0:  # Check if it's a creation command
                    product_id = line[2].get('product_id')
                    if product_id:
                        product_ids.add(product_id)
                        
            product_template_ids = set()
            for product_id in product_ids:
                product = self.env['product.product'].browse(product_id)
                if product.exists():
                    product_template_ids.add(product.product_tmpl_id.id)

            product_templates = self.env['product.template'].browse(list(product_template_ids))
            _logger.info(f" quote  {product_templates}")        
            
            
            if product_templates:
                _logger.info("Assigning products to product_quote_ids: %s", product_templates)
                quote.product_quote_ids = [(6, 0, product_templates.ids)]  # Use .ids here
            else:
                _logger.info("No products to assign to product_quote_ids")
        
        _logger.info("CustomerQuote creation completed")
        return quote

    @api.model    
    def write(self, vals):
        _logger.info("Starting update of CustomerQuote")
        _logger.info("Received vals for update: %s", vals)

        result = super(CustomerQuote, self).write(vals)

        # Check if we're not already in the process of updating product_quote_ids
        if not self.env.context.get('updating_product_quote_ids'):
            self.with_context(updating_product_quote_ids=True)._update_product_quote_ids()

        _logger.info("CustomerQuote update completed")
        return result

    def _update_product_quote_ids(self):
        for record in self:
            product_ids = record.quote_lines.mapped('product_id.id')
            product_templates = self.env['product.product'].browse(product_ids).mapped('product_tmpl_id')
            
            _logger.info(f"Updated quote {record.id} with product templates: {product_templates}")

            if product_templates:
                _logger.info("Updating products in product_quote_ids: %s", product_templates)
                record.product_quote_ids = [(6, 0, product_templates.ids)]
            else:
                _logger.info("No products to assign to product_quote_ids after update")
    
    def action_create_mo_dialog(self):
        """
        Action to open the Manufacturing Order creation dialog.
        Includes error handling and validation.
        """
        self.ensure_one()
        
        # Validate quote state
        if self.quote_status in ['draft','review']:
            raise UserError('Manufacturing Orders can only be created for quotes in draft state.')
            
        _logger.info('Triggered action_create_mo_dialog for quote ID: %s', self.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'create_mo_dialog',
            'name': 'Create Manufacturing Order',
            'params': {
                'quote_id': self.id,
                'default_date': fields.Date.today(),
                'company_id': self.customer_id.id,
            },
            'target': 'new',
            'context': self.env.context
        }

    
    @api.model
    def create_mo(self, quote_id, planned_date):
        quote = self.browse(quote_id)
        # Your logic to create MO using quote and planned_date
        # ...
        return True
    
    def action_create_mos(self):
        # This will open a wizard to select lines and create MOs
        return {
            'name': 'Create Manufacturing Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'create.mo.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_quote_id': self.id,
            }
        }


    
class CustomerQuoteLines(models.Model):
    _name = 'customer.quote.lines'
    _description = "Customer Quote Lines"

    quote_id = fields.Many2one('customer.quote', string="Quote", ondelete='cascade', required=True, help="The quote to which this line belongs.")
    product_id = fields.Many2one('product.product', string="Product", required=False, ondelete='set null', help="The product associated with this line.")
    product_type = fields.Selection([
        ('consu', 'Goods'),
        ('service', 'Service'),
    ], string="Product Type", related='product_id.type', readonly=True, help="The type of the product.")
    subtype = fields.Selection([('prod', 'Product'), ('service', 'Service'), ('estimate', 'Estimate')], string='Sub-type',  store=True,help="The subtype of the product.")
    #product_subtype = fields.Char(string="Product Subtype", compute='_compute_product_subtype', store=True, help="The subtype of the product.")
    pricing_qty = fields.Float(string="Quantity", default=1.0, required=True, help="The quantity of the product.")
    pricing_amounts = fields.Float(string="Unit Price", compute='_compute_pricing_amounts', store=True, help="The unit price of the product.")
    unit_price_transition =  fields.Float(string="Unit Price",store=True, help="The unit price to assign in the MO.")

    estimate_data = fields.Text(string="Pricing Tiers", store=True)
    estimate_data_qty = fields.Text(string="Pricing Tiers Qty", store=True)
    estimate_data_pricing = fields.Text(string="Pricing Tiers Selling Price", store=True)
    formatted_estimate_data = fields.Html(string="Formatted Estimate", compute="_compute_formatted_estimate_data",store=True)
    formatted_estimate_data_qty = fields.Html(string="Formatted Estimate Qty", compute="_compute_formatted_estimate_data_qty",store=True)
    formatted_estimate_data_pricing = fields.Html(string="Formatted Estimate Pricing", compute="_compute_formatted_estimate_data_pricing",store=True)

    lock_fields = fields.Boolean(related='quote_id.lock_fields', string="Lock Fields", readonly=True)

    @api.depends('product_id')
    def _compute_product_subtype(self):
        for line in self:
            line.product_subtype = line.product_id.type_of_good  # Example: Use product category as subtype

    @api.depends('product_id', 'pricing_qty')
    def _compute_pricing_amounts(self):
        for line in self:
            line.pricing_amounts = line.product_id.list_price  # Example: Use product's list price as unit price
            
            

    @api.depends('estimate_data')
    def _compute_formatted_estimate_data(self):
        for line in self:
            if line.estimate_data:

                # Escape special characters and add <br/> for newlines
                safe_data = html.escape(line.estimate_data.strip()).replace('\n', '<br/>')
                line.formatted_estimate_data = safe_data
            else:
                line.formatted_estimate_data = "No Estimate Available _compute_formatted_estimate_data"
                
                
    @api.depends('estimate_data')
    def _compute_formatted_estimate_data_qty(self):
        for line in self:
            if line.estimate_data:

                # Escape special characters and add <br/> for newlines
                safe_data = html.escape(line.estimate_data_qty.strip()).replace('\n', '<br/>')
                line.formatted_estimate_data_qty = safe_data
            else:
                line.formatted_estimate_data_qty = "No Estimate Available _compute_formatted_estimate_data_qty"
    
    @api.depends('estimate_data')
    def _compute_formatted_estimate_data_pricing(self):
        for line in self:
            if line.estimate_data:

                # Escape special characters and add <br/> for newlines
                safe_data = html.escape(line.estimate_data_pricing.strip()).replace('\n', '<br/>')
                line.formatted_estimate_data_pricing = safe_data
            else:
                line.formatted_estimate_data_pricing = "No Estimate Available _compute_formatted_estimate_data_pricing"
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Update estimate_data only temporarily in the view before saving
        if self.product_id:
            self.subtype = self.product_id.type_of_good
            estimate_datax = self._compute_estimate_data(self.product_id)
             # Check the return value of _compute_estimate_data
            _logger.info(f"estimate_datax {estimate_datax}")
            if not isinstance(estimate_datax, str):
                _logger.info("Updated estimate data (onchange): %s", estimate_datax.type)
                self.product_type = estimate_datax.type  # Set the warning message
                self.estimate_data = estimate_datax.name  # Set the warning message
                self.estimate_data_qty = "1"
                self.estimate_data_pricing = estimate_datax.list_price
            else:
                self.estimate_data = estimate_datax
                self.estimate_data_qty = self._compute_estimate_data_qty(self.product_id)
                self.estimate_data_pricing = self._compute_estimate_data_pricing(self.product_id)
                
    
    def _compute_estimate_data(self, product):
        """
        This method fetches and computes the related estimate data for the given product.
        It returns a string that will be stored in the estimate_data field.
        """
        if not product:
            return "No product selected."
        # Search for an estimate  linked to specific product
        estimates = self.env['customer.estimate'].search([
            ('product_id_for_estimate_draft', '=', product.product_tmpl_id.id)
        ])

        if estimates:   
            estimate_details = []
            for estimate in estimates:
                if estimate.name == product.name:
                    pricing_lines = estimate.estimate_pricing_line_ids
            
                    if pricing_lines:
                        # Create pricing info with two-column formatting
                        pricing_info = []
                        for line in pricing_lines:
                            quantity = f"{line.quantity:<5}"
                            price = f"{round(line.selling_price_with_commission, 2):>15}"
                            formatted_line = textwrap.dedent(f"{quantity}{price:<22}/EA").strip()
                            pricing_info.append(formatted_line)

                        # Join the pricing lines (no dedent needed here)
                        estimate_info = '\n'.join(pricing_info)
                    else:
                        estimate_info = "No pricing lines available."
                    
                    # Append only non-empty estimate info
                    if estimate_info.strip():  # Check if the result is not just whitespace
                        estimate_details.append(estimate_info)

            # Combine all details into a single string, avoiding unwanted newlines
            result = "\n".join(estimate_details)
            _logger.info(f"Estimate data: {result}")
            return result
        else:
            _logger.info(f"No estimates available for product {product.name}.")
            return product
        
    def _compute_estimate_data_qty(self, product):
        """
        This method fetches and computes the related estimate data for the given product.
        It returns a string that will be stored in the estimate_data field.
        """
        if not product:
            return "No product selected."

        estimates = self.env['customer.estimate'].search([
            ('product_id_for_estimate_draft', '=', product.product_tmpl_id.id)
        ])

        if not estimates:
            return "No estimates available for this product."

        estimate_details = []
        for estimate in estimates:
            if estimate.name == product.name:
                pricing_lines = estimate.estimate_pricing_line_ids
        
                if pricing_lines:
                    # Create pricing info with two-column formatting
                    pricing_info1 = []
                    for line in pricing_lines:
                        quantity = f"{line.quantity}"
                        formatted_line = textwrap.dedent(f"{quantity}").strip()
                        pricing_info1.append(formatted_line)

                    # Join the pricing lines (no dedent needed here)
                    estimate_info = '\n'.join(pricing_info1)
                else:
                    estimate_info = "No qty lines available."
                
                # Append only non-empty estimate info
                if estimate_info.strip():  # Check if the result is not just whitespace
                    estimate_details.append(estimate_info)

        # Combine all details into a single string, avoiding unwanted newlines
        result = "\n".join(estimate_details)
        
        return result
    
    
    def _compute_estimate_data_pricing(self, product):
        """
        This method fetches and computes the related estimate data for the given product.
        It returns a string that will be stored in the estimate_data field.
        """
        if not product:
            return "No product selected."

        estimates = self.env['customer.estimate'].search([
            ('product_id_for_estimate_draft', '=', product.product_tmpl_id.id)
        ])

        if not estimates:
            return "No estimates available for this product."

        estimate_details = []
        for estimate in estimates:
            if estimate.name == product.name:
                pricing_lines = estimate.estimate_pricing_line_ids
        
                if pricing_lines:
                    # Create pricing info with two-column formatting
                    pricing_info2 = []
                    for line in pricing_lines:
                        price = f"{round(line.selling_price_with_commission, 2)}"
                        formatted_line = textwrap.dedent(f"{price:<6} /EA").strip()
                        pricing_info2.append(formatted_line)

                    # Join the pricing lines (no dedent needed here)
                    estimate_info = '\n'.join(pricing_info2)
                else:
                    estimate_info = "No pricing lines available."
                
                # Append only non-empty estimate info
                if estimate_info.strip():  # Check if the result is not just whitespace
                    estimate_details.append(estimate_info)

        # Combine all details into a single string, avoiding unwanted newlines
        result = "\n".join(estimate_details)
        
        return result
    
    
    @api.model
    def create(self, vals):
        """
        Override the create method to ensure estimate_data is set when the record is created.
        """
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            estimx= self._compute_estimate_data(product)
            if not isinstance(estimx, str):
                vals['estimate_data'] = estimx.name
                vals['product_type'] = estimx.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = estimx.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_pricing'] = estimx.product_tmpl_id.list_price
            else:
                vals['estimate_data'] = estimx
                vals['product_type'] = product.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = product.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_qty'] = self._compute_estimate_data_qty(product)
                vals['estimate_data_pricing'] = self._compute_estimate_data_pricing(product)
                #_logger.info("Estimate data on create: %s", vals['estimate_data'])
        return super(CustomerQuoteLines, self).create(vals)

    def write(self, vals):
        """
        Override the write method to ensure estimate_data is updated when the record is written (saved).
        """
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            estimx= self._compute_estimate_data(product)
            if not isinstance(estimx, str):
                vals['estimate_data'] = estimx.name
                vals['product_type'] = estimx.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = estimx.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_qty'] = '1'
                vals['estimate_data_pricing'] = estimx.product_tmpl_id.list_price
            else:
                vals['estimate_data'] = estimx
                vals['product_type'] = product.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = product.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_qty'] = self._compute_estimate_data_qty(product)
                vals['estimate_data_pricing'] = self._compute_estimate_data_pricing(product)
                _logger.info("Estimate data on create: %s", vals['estimate_data'])
        return super(CustomerQuoteLines, self).write(vals)

class CreateMOWizard(models.TransientModel):
    _name = 'create.mo.wizard'
    _description = 'Create Manufacturing Order Wizard'

    quote_id = fields.Many2one('customer.quote', string='Customer Quote')
    line_ids = fields.Many2many('customer.quote.lines', string='Quote Lines')
    quote_name = fields.Char(   related='quote_id.name', string="Quote Name", readonly=True)
    quote_customer_id = fields.Many2one(related='quote_id.customer_id', string="Customer", readonly=True)
    quote_sales_team_user_id = fields.Many2one(
        related='quote_id.sales_team_user_id',
        string="Salesperson",
        readonly=True
    )
    @api.model
    def default_get(self, fields):
        res = super(CreateMOWizard, self).default_get(fields)
        if self._context.get('active_id'):
            quote = self.env['customer.quote'].browse(self._context['active_id'])
            if quote.exists():
                res['quote_id'] = quote.id
                res['line_ids'] = [(6, 0, quote.quote_lines.ids)]
        return res

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
        
    def action_create_mos(self):
        if len(self.line_ids) > 1:
            
            next_mo_sequence = self._get_last_mo_sequence()
            new_product = self.env['product.product'].create({
                'name': next_mo_sequence,  # Adjust naming convention as needed
                'type': 'consu',
                'type_of_good': 'estimate'
                # Add any other necessary fields for the new product
            })
            
            
            mo = self.env['mrp.production'].create({
                'product_id': new_product.id,  # Use the newly created product
                'product_qty': 1.0,
                'customer': self.env.user.id,
                'linked_quote_id':self.quote_id.id
            })
            
            manufactured_products = []
            c = 0
            for line in self.line_ids:
                c+=1
                manufactured_products.append({
                    'mo_id': mo.id,
                    'job_number':f"{next_mo_sequence} - {c}",
                    'product_id': line.product_id.id,
                    'quantity': line.pricing_qty,
                    'pricing_breakdown_qty':line.estimate_data_qty,
                    'pricing_breakdown_prices': line.estimate_data_pricing,
                    'schedule_date': fields.Date.today()


                })
            
            
            self.env['mrp.manufactured.product'].create(manufactured_products)
        else:
            # If there's only one product, create a simple MO
            line = self.line_ids[0]
            mo = self.env['mrp.production'].create({
                'product_id': line.product_id.id,  # Use the newly created product
                'product_qty': 1.0,
                'customer': self.env.user.id,
                'linked_quote_id':self.quote_id.id      
            })
            next_mo_sequence = self._get_last_mo_sequence()
            manufactured_products = []
            c= 0 
            for line in self.line_ids:
                c+=1
                manufactured_products.append({
                    'mo_id': mo.id,
                    'job_number':f"{next_mo_sequence} - {c}",
                    'product_id': line.product_id.id,
                    'quantity': line.pricing_qty,
                    'pricing_breakdown_qty':line.estimate_data_qty,
                    'pricing_breakdown_prices': line.estimate_data_pricing,
                    'schedule_date': fields.Date.today()

                })
            
            self.env['mrp.manufactured.product'].create(manufactured_products)
        
        return {'type': 'ir.actions.act_window_close'}

