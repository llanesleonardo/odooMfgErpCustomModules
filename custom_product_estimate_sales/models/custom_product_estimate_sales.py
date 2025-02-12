from odoo import models, api, fields
import logging
import html
import textwrap
import re
from odoo.exceptions import UserError,ValidationError

_logger = logging.getLogger(__name__)


class CustomProductEstimateSalesO(models.Model):
    _inherit = 'sale.order'
    user_message1 = fields.Char(string="User Message", readonly=True)
    manufacturing_order_id = fields.Many2one('mrp.production', string="Manufacturing Order", readonly=True)

            
class CustomProductEstimateSales(models.Model):
    _inherit = 'sale.order.line'
    
    user_message1 = fields.Char(string="User Message")
    # Store the estimate data in the database
    estimate_data = fields.Text(string="Pricing Tiers", store=True)
    estimate_data_qty = fields.Text(string="Pricing Tiers Qty", store=True)
    estimate_data_pricing = fields.Text(string="Pricing Tiers Selling Price", store=True)
    formatted_estimate_data = fields.Html(string="Formatted Estimate", compute="_compute_formatted_estimate_data")
    formatted_estimate_data_qty = fields.Html(string="Formatted Estimate Qty", compute="_compute_formatted_estimate_data_qty")
    formatted_estimate_data_pricing = fields.Html(string="Formatted Estimate Pricing", compute="_compute_formatted_estimate_data_pricing")

    # Store extracted values
    first_column_values = fields.Char(string="First Column Values", compute="_compute_column_values")
    second_column_values = fields.Char(string="Second Column Values", compute="_compute_column_values")
    order_due_date = fields.Date(string="Order Due Date")
    subtype = fields.Selection([('prod', 'Product'), ('service', 'Service'), ('estimate', 'Estimate')], string='Sub-type',  store=True)
    
    
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

    @api.depends('estimate_data')
    def _compute_column_values(self):
        for line in self:
            if line.estimate_data:
                first_column_pattern = r'^(\d+)'  # Match numbers at the start of the line with no leading whitespace

                
                # Extract first column values
                first_column = re.findall(first_column_pattern,line.estimate_data, re.MULTILINE)
                
                # Clean and join values
                joined_values = '\n'.join(value.strip() for value in first_column)
                
                # Set the cleaned result
                step = textwrap.dedent(joined_values).strip()
                line.first_column_values = f"\n{step}"

                # If you want to use second column values later
                        # Regular expression to match the second column (integers or decimal numbers)
                second_column_pattern =r'^\s*\d+\s+(\d+(\.\d+)?)' # Match second column values (integers or decimals)
                second_column = re.findall(second_column_pattern, line.estimate_data, re.MULTILINE)
                line.second_column_values = '\n'.join(value.strip() for value in second_column)
                # Extract only the numbers (excluding the decimal part)
                second_column_numbers = [value[0] for value in second_column]

                # Print the extracted second column values
                print(second_column_numbers)
            else:
                line.first_column_values = ''
                line.second_column_values = ''

               
    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Update estimate_data only temporarily in the view before saving
        if self.product_id:
            self.price_unit = 0
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
                self.tax_id = None
            else:
                self.estimate_data = estimate_datax
                self.estimate_data_qty = self._compute_estimate_data_qty(self.product_id)
                self.estimate_data_pricing = self._compute_estimate_data_pricing(self.product_id)
                self.tax_id = None

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        """
        This method updates the `price_unit` based on the computed selling price and handles errors gracefully.
        """
        if self.product_id and self.product_uom_qty != 0 :
            try:
                self.price_unit = self._compute_estimate_pline_selling_price(
                    self.product_id, self.product_uom_qty
                )
                self.user_message1 = ""  # Clear the message
            except UserError as e:
                # Show the message as a notification
                raise ValidationError(str(e))

    def _compute_estimate_pline_selling_price(self, product, product_uom_qty):
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
                        if line.quantity == product_uom_qty:
                            selling_price = round(line.selling_price_with_commission, 2)
                            _logger.info(f"Found exact matching pricing line: {line}")
                            return f"{selling_price}"
                        elif line.quantity < product_uom_qty:
                            if best_tier is None or line.quantity > best_tier.quantity:
                                best_tier = line

                    if best_tier:
                        selling_price = round(best_tier.selling_price_with_commission, 2)
                        _logger.info(f"Found best matching pricing line: {best_tier}")
                        return f"{selling_price}"
                    
                    _logger.warning(f"No suitable pricing line for quantity {product_uom_qty}.")
                    return f"{0}"
                else:
                    _logger.warning(f"No pricing lines available in estimate {estimate.name}.")
                    raise UserError("No pricing lines available.")

        _logger.error(f"No matching estimates for product {product.name}.")
        raise UserError("No estimates available for this product.")      

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
                self.tax_id = None
            else:
                vals['estimate_data'] = estimx
                vals['product_type'] = product.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = product.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_qty'] = self._compute_estimate_data_qty(product)
                vals['estimate_data_pricing'] = self._compute_estimate_data_pricing(product)
                self.tax_id = None
                #_logger.info("Estimate data on create: %s", vals['estimate_data'])
        return super(CustomProductEstimateSales, self).create(vals)

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
                  
                self.tax_id = None
            else:
                vals['estimate_data'] = estimx
                vals['product_type'] = product.product_tmpl_id.type  # Set the warning message
                vals['subtype'] = product.product_tmpl_id.type_of_good  # Set the warning message
                vals['estimate_data_qty'] = self._compute_estimate_data_qty(product)
                vals['estimate_data_pricing'] = self._compute_estimate_data_pricing(product)
                self.tax_id = None
                _logger.info("Estimate data on create: %s", vals['estimate_data'])
        return super(CustomProductEstimateSales, self).write(vals)
