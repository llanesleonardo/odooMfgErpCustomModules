# -*- coding: utf-8 -*-

import uuid
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError,UserError

from datetime import datetime
import math
import logging
_logger = logging.getLogger(__name__)
from pprint import pformat
from dateutil.relativedelta import relativedelta

class CustomerEstimate(models.Model):
    _name = "customer.estimate"
    _inherit = ['portal.mixin', 'mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Estimate"
    _order = 'id desc'

    #General Info----------------------------------------------------------------------------------------
    #name = fields.Char(string="Part Number", required=True)
    name = fields.Char(string="Part No", required=True, store=True)
    active = fields.Boolean(string="Active", default=True,store=True)
    part_description = fields.Text(string="Description",store=True)
    part_notes = fields.Text(string="Part Notes (Appears on job Traveler and Work Order)",store=True)
    pricing_uom = fields.Selection([('ea','ea'),('pc','pc')], string="Pricing Unit of Mesure", default='ea',store=True)
    lock_price = fields.Boolean(string="Lock Price",store=True)
    product_code_id = fields.Many2one('product.code', string="Product Code")
    inventory_code_id = fields.Many2one('inventory.code', string="Inventory GL Code")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account',
        string='Stock Valuation Account',
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        help="."
    )
    alternate_part_number = fields.Char(string="Alternate Part Number")
    pricing_method = fields.Selection([('Billing Rate','Billing Rate'),('Cost + Markup', 'Cost + Markup')], string="Price Calculation Method", default='Billing Rate')

    #pricing information relational field ---------------------------------------------------------------------------------------- 
    estimate_pricing_line_ids = fields.One2many('estimate.pricing.line', 'estimate_id', string="Pricing Lines")
    
    
    #Engineering----------------------------------------------------------------------------------------
    partner_id = fields.Many2one('res.partner', string="Customer Code",store=True)
    revision = fields.Char(string="Revision",store=True)
    drawing_link = fields.Char(string="Drawing Link",store=True)
    part_weight = fields.Char(string="Part Weight",store=True)
    commission_per = fields.Float(string="Commission Percentage",store=True)
    misc_tooling_charge = fields.Float(string="Misc / Tooling Charge",store=True)
    misc_tooling_description = fields.Text(string="Misc Tooling Description",store=True)
    routed_by = fields.Many2one('res.users', string="Routed By",store=True, default=lambda self: self.env.user.id)
    date_routed = fields.Datetime(string="Date Routed",store=True,default=fields.Datetime.now)
   
    #Calculator
    number_of_bars = fields.Integer(string="Number of Bars",default=1)
    bar_size = fields.Float(string="Bar Size")
    tool_bar = fields.Float(string="Tool Bar Size") #tool size
    bar_end_loss = fields.Float(string="Bar End Loss")
    cut_off_per_part = fields.Float(string="Cut Off Per Part")
    stock_allowance = fields.Float(string="Stock Allowance")
    facing_allowance_per_part = fields.Float(string="Facing Allowance Per Part")
    result = fields.Float(string="Pcs", compute='_compute_result', readonly=True)
    result_rounded_lowest = fields.Float(string="Pcs Rounded Lowest", readonly=True)


    # Link Estimate to Products (product type estimate, this will be use when listing product in the quote module)
    product_id_for_estimate_draft = fields.Many2one('product.template', string="Linked Product", required=False)
    

    #material info relational field ----------------------------------------------------------------------------------------  
    estimate_material_line_ids = fields.One2many('estimate.material.line', 'estimate_id', string="Material Cost Info")
    #material_unit_cost = fields.Float()
    

    #routing info relational field ---------------------------------------------------------------------------------------- 
    work_center_ids = fields.One2many('estimate.work.center', 'estimate_id', string="Routing Cost Info")

    total_unit_cost = fields.Float(string="Total Unit Cost", compute="get_total_unit_cost", store=True)
    total_pc_unit_cost = fields.Float(string="Total Pc Unit Cost", compute="get_total_pc_unit_cost", store=True)
    initial_labor_rate = fields.Float(string="Initial Labor rate", compute="compute_initial_labor_rate", store=True)
    min_labor_cost = fields.Float(string="Min Labor rate", compute="compute_min_labor_cost", store=True)
    decrease_rate = fields.Float(string="Decrease rate", default=0.5)
    setup_unit_cost = fields.Float(string="Set up rate", store=True, compute="compute_setup_cost")
    burden_rate = fields.Float(string="Burden Rate", store=True, compute="compute_burden_cost")
    total_setup_time = fields.Float(string="Total Setup Time", store=True, compute="compute_total_setup_time")
    total_cycle_time = fields.Float(string="Total Cycle Time", store=True, compute="compute_total_cycle_time")
    bar_unit = fields.Selection([('ea', 'ea'),('pc', 'pc')], string="Unit", compute="get_bar_unit", store=True)
    total_cycle_rate = fields.Float(string="Total Cycle Rate", compute="compute_total_cycle_rate", store=True)
    
    #routing info 2
    setup_time_total_wc = fields.Float(string="Setup Time Total")
    cycle_time_total_wc = fields.Float(string="Cycle Time Total")
    setup_rate_amt_total_wc = fields.Float(string="Setup Rate Total")
    cycle_rate_amt_total_wc = fields.Float(string="Cycle Rate Total")
    burden_rate_amt_total_wc = fields.Float(string="Burden Rate Total")
    labor_rate_total_wc = fields.Float(string="Labor Rate Total")
    
    
    
    
    
    
    def action_create_customer_quote(self):
        for estimate in self:
            quote_vals = {
                'name': f"Q-{estimate.name}-{fields.Date.today()}",
                'customer_id': estimate.partner_id.id,
                'expiration_date': fields.Date.today() + relativedelta(days=30),  # Example: set expiration to 30 days from now
                'quote_date': fields.Date.today(),
                'sales_team_user_id': estimate.routed_by.id,  # Assuming you have a user_id field
                'note': estimate.part_notes,  # If you have notes in your estimate
                'quote_status': 'draft',
            }
            
            new_quote = self.env['customer.quote'].create(quote_vals)
            product_product = self.env['product.product'].search([('product_tmpl_id', '=', self.product_id_for_estimate_draft.id)], limit=1)
            # Create quote lines based on estimate pricing lines
           
            self.env['customer.quote.lines'].create({
                    'quote_id': new_quote.id,
                    'product_id': product_product.id if product_product else False,
                    'product_type': 'consu',
                    'subtype': 'estimate'
                    # Add other fields as necessary
                })
            
            # Optionally, open the newly created quote in a new window
        return {
                'name': 'Customer Quote',
                'view_mode': 'form',
                'res_model': 'customer.quote',
                'res_id': new_quote.id,
                'type': 'ir.actions.act_window',
        }
            
    #------------------------------------------------------------------------------------------------------
    """
    Compute the result and result_rounded_lowest based on number_of_bars, bar_size, and tool_bar.

    This function calculates the result by multiplying the number of bars by the ratio of bar size to tool bar.
    It then sets result_rounded_lowest to the floor value of the result.
    If bar_size or tool_bar or number_of_bars is not set, the result is set to 0.
    After computation, it triggers the action to divide material cost.

    The function is triggered when any of the dependent fields (number_of_bars, bar_size, tool_bar, result_rounded_lowest) change.

    :return: None
    """
    @api.depends('number_of_bars', 'bar_size', 'tool_bar','result_rounded_lowest')
    def _compute_result(self):
        for record in self:
            if record.bar_size and record.tool_bar and record.number_of_bars:
                record.result_rounded_lowest = 0
                record.result = record.number_of_bars * (record.bar_size / record.tool_bar)
                record.result_rounded_lowest = math.floor(record.result)
                self.action_divide_material_cost()
            else:
                record.result = 0
    
    """
    Trigger the calculation of result and result_rounded_lowest.

    This method is designed to be called when a button is clicked in the user interface.
    It invokes the _compute_result method to recalculate the result and result_rounded_lowest fields.
    This allows for manual recalculation of these fields, which can be useful in scenarios where
    automatic recalculation is not triggered or when a user wants to force a recalculation.

    :return: True (to indicate successful execution)
    """
    def calculate(self):
        # This method will be called when the button is clicked
        self._compute_result()
        return True
    #------------------------------------------------------------------------------------------------------
    

    def _reorder_pricing_lines(self):
        """Sort pricing lines by quantity and update their sequence."""
        # Assuming 'estimate_pricing_line_ids' is the field name for pricing lines
        lines = self.estimate_pricing_line_ids.sorted('quantity')
        _logger.info(f"_reorder_pricing_lines {lines}")
        for index, line in enumerate(lines, start=1):
            line.sequence = index * 10  # Persist the sequence in increments of 10
        
    # Call this method when needed, for example:
    # self._reorder_pricing_lines()
        
    """
    Create a new CustomerEstimate record and associated product.

    This method overrides the default create method to add custom behavior:
    1. It calls the superclass create method to create the actual record.
    2. It calls a custom method to create a product associated with this estimate.

    :param vals: Dictionary containing field values for the new record
    :type vals: dict
    :return: Newly created CustomerEstimate record
    :rtype: CustomerEstimate

    Note: This method is automatically called by Odoo when a new record is being created.
    """
    @api.model
    def create(self, vals):
        self._reorder_pricing_lines()
        record = super(CustomerEstimate, self).create(vals)
        self.create_product_from_record(record)
        
        return record



    """
    Create a new product based on the customer estimate record.

    This method creates a new product in the product.template model using information
    from the customer estimate record. It performs the following steps:
    1. Retrieves the first pricing line from the estimate record.
    2. If a pricing line exists, it creates a dictionary of product values using data
    from the estimate and pricing line.
    3. Creates a new product using these values.
    4. Links the newly created product back to the estimate record.
    5. Logs the creation of the new product or any errors that occur during the process.

    :param record: The customer estimate record from which to create the product
    :type record: customer.estimate

    :return: None

    :raises: Logs any exception that occurs during the product creation process

    Note: This method is typically called after a new customer estimate record is created
    or updated. It ensures that each estimate has an associated product that can be used
    in sales processes.
    """
    def create_product_from_record(self, record):
        _logger.info("create_product_from_record called for record: %s", record)
        try:
            first_pricing_line = record.estimate_pricing_line_ids[:1] or None
            BaseListPriceForProduct = 0
            BaseUnitCostforProduct = 0
            #_logger.info(f"irst_pricing_line ************************ {first_pricing_line.read()}")
            if first_pricing_line:
                if first_pricing_line.quantity == 1:
                    BaseListPriceForProduct = first_pricing_line.selling_price
                    BaseUnitCostforProduct = first_pricing_line.unit_cost
                    _logger.info(f" first_pricing_line.quantity {first_pricing_line.quantity} (BaseListPriceForProduct + BaseUnitCostforProduct) {BaseListPriceForProduct} {BaseUnitCostforProduct}")
                else:
                    BaseListPriceForProduct = 0
                    BaseUnitCostforProduct = 0   
                    _logger.info(f" first_pricing_line.quantity {first_pricing_line.quantity} (BaseListPriceForProduct + BaseUnitCostforProduct) {BaseListPriceForProduct} {BaseUnitCostforProduct}") 
                    
                product_vals = {
                        'name': record.name,
                        'type': 'consu',
                        'type_of_good':'estimate',
                        'list_price':  BaseListPriceForProduct or 0,
                        'standard_price': BaseUnitCostforProduct or 0,
                        'active':True,
                        'sale_ok': True,  # Can be sold
                        'purchase_ok': False,  # Can be purchased
                        'description': record.part_description or '',
                        'is_storable': True,
                        'service_tracking': 'no',  # Default value, change if needed
                        'categ_id': self.env.ref('product.product_category_all').id,  # Default category, change if needed
                        'uom_id': self.env.ref('uom.product_uom_unit').id,  # Default unit of measure, change if needed
                        'uom_po_id': self.env.ref('uom.product_uom_unit').id,  # Default purchase UoM, change if needed
                        'tracking': 'none',  # Default tracking method, change if needed
                        'purchase_line_warn': 'no-message',  # Default warning setting, change if needed
                        'sale_line_warn': 'no-message',  # Default warning setting, change if needed
                        
                }
                    #_logger.info(" first_pricing_line : %s", first_pricing_line)
                    
                new_product = self.env['product.template'].create(product_vals)
                #fields_info = self.env['product.template'].fields_get()
                #print(fields_info.keys())
                _logger.info(f" EXECUTIION new_product = self.env['product.template'].create(product_vals) {new_product}  ")
                    # Link the new product to the estimate
                record.product_id_for_estimate_draft = new_product.id
                    
                    # Add the new product to the estimate's product_ids
                    #record.product__type_estimate_id = [(4, new_product.id)]
                    #_logger.info("New product created: %s", new_product)
            else:
                product_vals = {
                        'name': record.name,
                        'type': 'prod',
                        'type_of_good':'estimate',
                        'list_price':  0,
                        'standard_price': 0,
                        'active':True,
                        'sale_ok': True,  # Can be sold
                        'purchase_ok': False,  # Can be purchased
                        'description': '',
                        'service_tracking': 'no',  # Default value, change if needed
                        'is_storable': True,
                        'categ_id': self.env.ref('product.product_category_all').id,  # Default category, change if needed
                        'uom_id': self.env.ref('uom.product_uom_unit').id,  # Default unit of measure, change if needed
                        'uom_po_id': self.env.ref('uom.product_uom_unit').id,  # Default purchase UoM, change if needed
                        'tracking': 'none',  # Default tracking method, change if needed
                        'purchase_line_warn': 'no-message',  # Default warning setting, change if needed
                        'sale_line_warn': 'no-message',  # Default warning setting, change if needed
                }
                  
                new_product = self.env['product.template'].create(product_vals)
                    #fields_info = self.env['product.template'].fields_get()
                    #print(fields_info.keys())
                _logger.info(f" EXECUTIION new_product = self.env['product.template'].create(product_vals) {new_product}  ")
                        # Link the new product to the estimate
                record.product_id_for_estimate_draft = new_product.id
        except Exception as e:
            _logger.error("Error in create_product_from_record: %s", str(e))


    """
    Compute the total cycle rate for the record based on associated work centers.

    This method calculates the sum of cycle rate amounts from all associated work centers.
    It is automatically triggered when the cycle_rate_amt of any related work center changes.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a total_cycle_rate variable to 0.
    b. Iterates through each work center, adding its cycle_rate_amt to the total.
    c. Sets the record's total_cycle_rate field to the computed sum.
    3. If a record has no associated work centers, sets its total_cycle_rate to 0.

    :return: None

    Note: This is a computed method, decorated with @api.depends. It will automatically 
    update the total_cycle_rate field whenever the cycle_rate_amt of any related 
    work center changes, ensuring that the total is always up-to-date.
    """
    
    @api.depends('work_center_ids.cycle_rate_amt')
    def compute_total_cycle_rate(self):
        for rec in self:
            if rec.work_center_ids:
                total_cycle_rate = 0
                for wc in rec.work_center_ids:
                    total_cycle_rate += wc.cycle_rate_amt
                rec.total_cycle_rate = total_cycle_rate
            else:
                rec.total_cycle_rate = 0
        _logger.info("compute_total_cycle_rate method completed")           
                
                
    """
    Compute the bar unit for each estimate based on its material lines.

    This method determines the bar unit for an estimate by examining its material lines.
    It is triggered when estimate_material_line_ids or their units change.

    The computation follows these steps:
    1. If there are no material lines, sets bar_unit to 0 for all records and returns.
    2. For each record with material lines:
    a. Filters for lines with products of type 'consu' or 'estimate'.
    b. If such a line is found, sets bar_unit to that line's unit.
    c. If no such line is found, sets bar_unit to 0.
    3. If a record has no material lines, sets its bar_unit to 0.

    The bar_unit is a hidden variable used to determine if the estimate will be 
    calculated by 'ea' (each) or 'pc' (piece).

    :return: None

    Note: This is a computed method, decorated with @api.depends. It will automatically 
    update the bar_unit field whenever the material lines or their units change. 
    The method includes extensive logging for debugging purposes.
    """
    
    @api.depends('estimate_material_line_ids','estimate_material_line_ids.unit')
    def get_bar_unit(self):
        # teh bar unit variable is a hidden variable and it has the same value as the product_uom variable (it is use to test if the estimate is going to be calculate by ea or pc)
        # Early return if estimate_material_line_ids is empty
        if not self.estimate_material_line_ids:
            #_logger.info("estimate_material_line_ids is empty, setting bar_unit to 0")
            for rec in self:
                rec.bar_unit = 0
            return

        for rec in self:
            if rec.estimate_material_line_ids:
                line_id = rec.estimate_material_line_ids.filtered(lambda l: l.product_id.type in ['consu', 'estimate'])
                # line_id = rec.estimate_material_line_ids.filtered(lambda l: l.product_id.name == 'bar')
                if line_id:
                    rec.bar_unit = line_id[-1].unit
                    #_logger.info("Bar Object: %s", line_id.read())
                else:
                    #_logger.info("No 'bar' product found, setting bar_unit to 0")
                    rec.bar_unit = 0
            else:
                #_logger.info("No estimate_material_line_ids for this record, setting bar_unit to 0")
                rec.bar_unit = 0
        
        _logger.info("get_bar_unit method completed")

    """
    Compute the total setup time for the estimate based on associated work centers.

    This method calculates the sum of setup times from all associated work centers.
    It is automatically triggered when the setup_time of any related work center changes.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a total_setup_time variable to 0.
    b. Iterates through each work center, adding its setup_time to the total.
    c. Sets the record's total_setup_time field to the computed sum.
    3. If a record has no associated work centers, sets its total_setup_time to 0.

    :return: None

    Note: This is a computed method, decorated with @api.depends. It will automatically 
    update the total_setup_time field whenever the setup_time of any related 
    work center changes, ensuring that the total is always up-to-date.

    The method includes a log message upon completion for debugging purposes.
    """
    @api.depends('work_center_ids')
    def compute_total_setup_time(self):
        for rec in self:
            if rec.work_center_ids:
                total_setup_time = 0
                for wc in rec.work_center_ids:
                    total_setup_time += wc.setup_time
                rec.total_setup_time = total_setup_time
            else:
                rec.total_setup_time = 0
        
        _logger.info("compute_total_setup_time method completed")
        
    """
    Compute the total cycle time for the estimate based on associated work centers.

    This method calculates the sum of cycle times from all associated work centers.
    It is automatically triggered when the cycle_time of any related work center changes.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a total_cycle_time variable to 0.
    b. Iterates through each work center, adding its cycle_time to the total.
    c. Sets the record's total_cycle_time field to the computed sum.
    3. If a record has no associated work centers, sets its total_cycle_time to 0.

    :return: None

    Note: This is a computed method, decorated with @api.depends. It will automatically 
    update the total_cycle_time field whenever the cycle_time of any related 
    work center changes, ensuring that the total is always up-to-date.

    The method includes a log message upon completion for debugging purposes.
    (Note: The log message currently refers to setup_time, which appears to be a typo and should be updated to cycle_time.)
    """      
    @api.depends('work_center_ids')
    def compute_total_cycle_time(self):
        for rec in self:
            if rec.work_center_ids:
                total_cycle_time = 0
                for wc in rec.work_center_ids:
                    total_cycle_time += wc.cycle_time
                    #_logger.info(f"LOOP total_cycle_time {total_cycle_time} wc {wc.read()}")
                rec.total_cycle_time = total_cycle_time
                #_logger.info(f"rec.total_cycle_time {rec.total_cycle_time}")                
            else:
                rec.total_cycle_time = 0
        _logger.info("compute_total_cycle_time method completed")
        
    """
    Compute the minimum labor cost for each record.

    This method calculates the minimum labor cost by dividing the initial labor rate by 2.7.
    It is automatically triggered when either the initial_labor_rate or decrease_rate fields change,
    although the current implementation only uses initial_labor_rate.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record, calculates the min_labor_cost by dividing initial_labor_rate by 2.7.
    3. Sets the record's min_labor_cost field to the computed value.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the min_labor_cost field whenever initial_labor_rate or decrease_rate changes.
    - The current implementation does not use the decrease_rate field, which is included 
    in the @api.depends decorator. This might be a point for future review or enhancement.
    - The division by 2.7 is a fixed factor. The reasoning behind this specific value 
    should be documented or reviewed if it's not a standard industry practice.
    - The method includes a log message upon completion, but the message incorrectly 
    refers to 'compute_total_cycle_time'. This should be updated to reflect the correct method name.

    """
    @api.depends('initial_labor_rate', 'decrease_rate')
    def compute_min_labor_cost(self):
        for rec in self:
            rec.min_labor_cost = rec.initial_labor_rate / 2.5
        _logger.info("compute_min_labor_cost method completed")
    
    """
    Compute the initial labor rate for each record based on associated work centers.

    This method calculates the sum of labor rates from all associated work centers.
    It is automatically triggered when the work_center_ids field changes, which could
    occur when work centers are added, removed, or modified.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a labor variable to 0.
    b. Iterates through each work center, adding its labor_rate to the total.
    c. Sets the record's initial_labor_rate field to the computed sum.
    3. If a record has no associated work centers, sets its initial_labor_rate to 0.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the initial_labor_rate field whenever the set of associated work centers changes.
    - The method assumes that each work center has a labor_rate field.
    - The initial_labor_rate is set to the sum of all work center labor rates, which 
    might need review if this is not the intended behavior (e.g., if it should be an average instead).
    - The method includes a log message upon completion for debugging purposes.

    """   
    @api.depends('work_center_ids')
    def compute_initial_labor_rate(self):
        for rec in self:
            if rec.work_center_ids:
                labor = 0
                for wc in rec.work_center_ids:
                    labor += wc.labor_rate
                rec.initial_labor_rate = labor
            else:
                rec.initial_labor_rate = 0
        
        _logger.info("compute_initial_labor_rate method completed")

    """
    Compute the setup unit cost for each record based on associated work centers.

    This method calculates the sum of setup rate amounts from all associated work centers.
    It is automatically triggered when the work_center_ids field changes, which could
    occur when work centers are added, removed, or modified.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a total variable to 0.
    b. Iterates through each work center, adding its setup_rate_amt to the total.
    c. Sets the record's setup_unit_cost field to the computed sum.
    3. If a record has no associated work centers, sets its setup_unit_cost to 0.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the setup_unit_cost field whenever the set of associated work centers changes.
    - The method assumes that each work center has a setup_rate_amt field.
    - The setup_unit_cost is set to the sum of all work center setup rate amounts.
    - The method includes a log message upon completion, but the message incorrectly 
    refers to 'compute_initial_labor_rate'. This should be updated to reflect the correct method name.

    """
    @api.depends('work_center_ids')
    def compute_setup_cost(self):
        for rec in self:
            if rec.work_center_ids:
                total = 0
                for wc in rec.work_center_ids:
                    total += wc.setup_rate_amt
                rec.setup_unit_cost = total
            else:
                rec.setup_unit_cost = 0
        _logger.info("compute_initial_labor_rate method completed")
        
    """
    Compute the burden rate for each record based on associated work centers.

    This method calculates the sum of burden rate amounts from all associated work centers.
    It is automatically triggered when the work_center_ids field changes, which could
    occur when work centers are added, removed, or modified.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated work centers:
    a. Initializes a burden variable to 0.
    b. Iterates through each work center, adding its burden_rate_amt to the total.
    c. Sets the record's burden_rate field to the computed sum.
    3. If a record has no associated work centers, sets its burden_rate to 0.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the burden_rate field whenever the set of associated work centers changes.
    - The method assumes that each work center has a burden_rate_amt field.
    - The burden_rate is set to the sum of all work center burden rate amounts.
    - The variable name 'br' is used in the loop, which might be confusing. Consider 
    changing it to 'wc' for consistency with other similar methods.
    - The method includes a log message upon completion, but the message incorrectly 
    refers to 'compute_initial_labor_rate'. This should be updated to reflect the correct method name.

    """
    @api.depends('work_center_ids')
    def compute_burden_cost(self):
        for rec in self:
            if rec.work_center_ids:
                burden = 0
                for br in rec.work_center_ids:
                    burden += br.burden_rate_amt
                rec.burden_rate = burden
            else:
                rec.burden_rate = 0
        _logger.info("compute_burden_cost method completed")
        
    """
    Compute the total unit cost for each record based on associated material lines.

    This method calculates the sum of unit costs from all associated estimate material lines.
    It is automatically triggered when the unit_cost of any related estimate material line changes.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated estimate material lines:
    a. Initializes a total variable to 0.
    b. Iterates through each material line, adding its unit_cost to the total.
    c. Sets the record's total_unit_cost field to the computed sum.
    3. If a record has no associated estimate material lines, sets its total_unit_cost to 0.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the total_unit_cost field whenever the unit_cost of any related 
    estimate material line changes.
    - The method assumes that each estimate material line has a unit_cost field.
    - The total_unit_cost is set to the sum of all material line unit costs, which 
    might need review if this is not the intended behavior (e.g., if it should 
    account for quantities or other factors).
    - Unlike some other compute methods in this class, this one does not include 
    a log message upon completion. Consider adding one for consistency and debugging purposes.

    """
    @api.depends('estimate_material_line_ids.unit_cost')
    def get_total_unit_cost(self):
        for rec in self:
            if rec.estimate_material_line_ids:
                total = 0
                for m_line in rec.estimate_material_line_ids:
                    total += m_line.unit_cost
                rec.total_unit_cost = total
            else:
                rec.total_unit_cost = 0
        _logger.info("get_total_unit_cost method completed")

    """
    Compute the total PC unit cost for each record based on associated material lines.

    This method calculates the sum of PC unit costs from all associated estimate material lines,
    considering both the pcs_unit_divided and unit costs for service-type products. 
    It is automatically triggered when the pcs_unit_divided or unit of any related estimate material line changes.

    The computation follows these steps:
    1. Iterates through each record in the recordset.
    2. For each record with associated estimate material lines:
    a. Initializes a total variable to 0.
    b. Iterates through each material line:
        - If the product type is 'service' and the record's bar_unit is 'pc', 
            it assigns the unit cost of that material line to servicecost.
        - Otherwise, servicecost is set to 0.
    c. Adds the sum of pcs_unit_divided and servicecost to the total.
    d. Sets the record's total_pc_unit_cost field to the computed sum.
    3. If a record has no associated estimate material lines, sets its total_pc_unit_cost to 0.

    :return: None

    Note: 
    - This is a computed method, decorated with @api.depends. It will automatically 
    update the total_pc_unit_cost field whenever relevant fields in associated 
    estimate material lines change.
    - The method assumes that each estimate material line has both pcs_unit_divided 
    and unit fields, as well as a product_id with a type attribute.
    - The logic for calculating service costs is conditional based on product type 
    and bar unit, which should be reviewed to ensure it meets business requirements.
    - The method includes a log message upon completion, but it incorrectly refers 
    to 'get_total_unit_cost'. This should be updated to reflect the correct method name.

    """
    @api.depends('estimate_material_line_ids.pcs_unit_divided','estimate_material_line_ids.unit')
    def get_total_pc_unit_cost(self):
        for rec in self:
            if rec.estimate_material_line_ids:
                total = 0
                for m_line in rec.estimate_material_line_ids:
                    servicecost = 0
                    if m_line.product_id.type == 'service' and m_line.unit == 'ea':
                        servicecost = m_line.unit_cost
                        #m_line.pcs_unit_divided = m_line.unit_cost
                    else:
                        servicecost = 0
                           
                    total += m_line.pcs_unit_divided  + servicecost
                    
                rec.total_pc_unit_cost = total
            else:
                rec.total_pc_unit_cost = 0
        _logger.info("get_total_unit_cost method completed")
        
    """
    Override the default_get method to set default values for a new CustomerEstimate record.

    This method is called when creating a new CustomerEstimate record and is used to 
    initialize default values for specified fields. It performs the following steps:
    1. Calls the superclass's default_get method to retrieve existing default values.
    2. Searches for all work center templates in the database.
    3. Initializes an empty list to hold tuples representing the default work center lines.
    4. Iterates through each work center template:
    a. Appends a tuple to the list containing default values for workcenter_id, setup_time, 
        cycle_time, setup_unit, and cycle_unit.
    5. If any work centers were found, adds the list of tuples to the defaults under the 
    'work_center_ids' field.
    6. Logs a message indicating that the default_get method has completed its execution.

    :param fields: List of fields for which default values are requested
    :type fields: list

    :return: A dictionary of default values for the specified fields
    :rtype: dict

    Note:
    - This method ensures that when a new CustomerEstimate record is created, it is pre-filled 
    with relevant work center information, enhancing user experience and reducing manual input.
    - The method includes a log message upon completion for debugging purposes.

    """
    @api.model
    def default_get(self, fields):
        defaults = super(CustomerEstimate, self).default_get(fields)
        work_center_ids = self.env['workcenter.template'].search([])
        lst = []
        for work_center in work_center_ids:
            lst.append((0,0,{
                'workcenter_id': work_center.id,
                'setup_time': work_center.setup_time,
                'cycle_time': work_center.cycle_time,
                'setup_unit': 'M',
                'cycle_unit': 'M',
            }))
        if lst:
            defaults['work_center_ids'] = lst
        
        _logger.info("default_get(self, fields) for setting default values for workcenters method completed")
        return defaults
        
    """
    Divide the material cost across related material lines.

    This method distributes the material cost from the current record to its associated 
    material lines based on specific conditions. It performs the following steps:
    1. Checks if the result_rounded_lowest field is set; if not, raises a ValidationError.
    2. Iterates through each related estimate material line:
    a. For material lines with product types 'consu' or 'estimate':
        - If the line has a unit:
            - If the unit is 'pc', it divides the unit cost by result_rounded_lowest and 
            assigns it to pcs_unit_divided.
            - If the unit is not 'pc', it sets pcs_unit_divided to 0.
        - If no unit is set, raises a ValidationError indicating that a Unit of Measurement must be set.
    3. Logs a message upon completion of the method.

    :return: None

    Note:
    - This method ensures that material costs are accurately divided among relevant 
    material lines, which is crucial for proper cost accounting in estimates.
    - The method includes validation checks to ensure that necessary fields are populated 
    before performing calculations, thus preventing runtime errors.

    """       
        
    def action_divide_material_cost(self):
        """Divide the material cost across related material lines."""
        for record in self:
            if not record.result_rounded_lowest:
                raise ValidationError("Result Rounded Lowest is not set.")

            # Loop through related material lines
            for line in record.estimate_material_line_ids:
                if line.product_id.type in ['consu', 'estimate']:
                    if line.unit:
                        if line.unit == 'pc':
                            if line.unit_cost:
                                line.pcs_unit_divided= 0
                                line.pcs_unit_divided = line.unit_cost / record.result_rounded_lowest
                        else:
                                line.pcs_unit_divided = 0
                    else:
                        raise ValidationError("Set a Unit of Measurement") 
        _logger.info("action_divide_material_cost method completed")
        
    
class ProductCode(models.Model):
    _name = 'product.code'
    _description = "Product Code"
    _order = "id desc"

    name = fields.Char(string="Product Code", required=True)


class InventoryCode(models.Model):
    _name = 'inventory.code'
    _description = "Inventory Code"
    _order = "id desc"

    name = fields.Char(string="Inventory Code", required=True)

class EstimatePricingLine(models.Model):
    _name = 'estimate.pricing.line'
    _description = "Description"

    quantity = fields.Float(string="Quantity", store=True)
    unit_cost = fields.Float(string="Unit Cost", store=True, compute="compute_cost_price")
    selling_price = fields.Float(string="Selling Price", store=True, compute="compute_selling_price")
    selling_price_with_commission = fields.Float(string="Selling Price + Commission", store=True, compute="compute_selling_price_with_commission")
    commission_amt = fields.Float(string="Commission", store=True, compute="compute_commission_amount")
    profit_margin = fields.Float(string="Profit Margin", store=True)
    total_profit = fields.Float(string="Total Profit", compute="compute_total_job_profit", store=True)
    total_job_time = fields.Float(string="Total job Time", store=True)
    avg_hourly = fields.Float(string="Avg Hourly", store=True)
    estimate_id = fields.Many2one('customer.estimate', string="Estimate")
    unit_labor_rate = fields.Float(string="Unit Labor Rate", store=True, compute="compute_workcenter_rates")
    unit_setup_cost = fields.Float(string="Unit Setup cost", store=True, compute="compute_setup_unit_cost")
    unit_burden_rate = fields.Float(string="Unit  Burden rate", store=True, compute="compute_burden_cost")
    hours_to_produce = fields.Float(string="Hours", store=True, compute="compute_hours_to_produce")
    
    # New field to store a filtered product type value
    product_types_summary = fields.Char(string="Material Cost", compute='compute_product_types_summary', store=True)
    product_price_based_on_qty = fields.Float(string="Price based on qty", store=True)
    product_price_based_on_qty_summary = fields.Char(string="Price based on qty", store=True)
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    #ESTIMATE PRICING BREAKDOWN METHODS
    
    def _calculate_material_cost(self):
        self.ensure_one()
        
        bar_unit = self.estimate_id.bar_unit
        #fetch all material lines
        material_lines = self.estimate_id.estimate_material_line_ids
        #filter material lines based on product type 'consu', 'estimate'
        product_only_good_estimate = material_lines.filtered(lambda l: l.product_id.type in ['consu', 'estimate'])
        #filter material lines based on product type 'service'
        product_only_services = material_lines.filtered(lambda l: l.product_id.type == 'service')
        #quantity for pricing breakdown if no value assign 1
        quantity_for_pricing_breakdown = self.quantity if self.quantity else 1
        total_material_cost = 0
        
        
        
        #if bar_unit is 'ea' then calculate the price based on quantity
        if bar_unit == "ea":
            unique_entries = set()
            for line in product_only_good_estimate:
                applicable_tiers = line.tiered_pricing_ids.filtered(lambda t: t.quantity <= quantity_for_pricing_breakdown)
                if applicable_tiers:
                    best_tier = max(applicable_tiers, key=lambda t: t.quantity)
                    total_material_cost += best_tier.price
                    entry = f"{line.product_id.product_tmpl_id.name} - $ {best_tier.price:.2f}"
                    #{self.product_price_based_on_qty_summary}/{best_tier.price:.2f}-
                else:
                    total_material_cost += line.unit_cost  # Use unit_cost if no applicable tier
                    entry = f"{line.product_id.product_tmpl_id.name} - $ {line.unit_cost:.2f}"
                    #{self.product_price_based_on_qty_summary}{line.unit_cost:.2f}-
                unique_entries.add(entry)
                   # Join unique entries
                self.product_price_based_on_qty_summary = " / ".join(sorted(unique_entries))
                # Remove leading "False /" if present
                if self.product_price_based_on_qty_summary.startswith("False /"):
                    self.product_price_based_on_qty_summary = self.product_price_based_on_qty_summary[7:].strip()
        else:
            # Calculate the sum if the unit is not 'ea' is 'pcs'
            total_material_cost = sum(product_only_good_estimate.mapped('pcs_unit_divided')) if product_only_good_estimate else 0

        # Sum of services unit cost
        services_sum_total = sum(product_only_services.mapped('unit_cost')) if product_only_services else 0
        # Return the total material cost and services sum total
        return total_material_cost, services_sum_total

    @api.depends('estimate_id.estimate_material_line_ids', 'estimate_id.bar_unit', 'quantity','estimate_id.estimate_material_line_ids.pcs_unit_divided','estimate_id.estimate_material_line_ids.unit_cost')
    def compute_product_types_summary(self):
        for rec in self:
            total_material_cost, services_sum_total = rec._calculate_material_cost()
            rec.product_types_summary = total_material_cost + services_sum_total
        
     #    @api.depends('estimate_id','estimate_id.estimate_material_line_ids','unit_cost', 'unit_labor_rate', 'unit_burden_rate', 'commission_amt', 'estimate_id.commission_per', 'estimate_id.bar_unit', 'product_types_summary', 'estimate_id.bar_unit', 'estimate_id.total_pc_unit_cost', 'estimate_id.total_unit_cost', 'quantity')
    @api.depends('unit_cost','quantity','profit_margin','estimate_id.bar_unit', 'estimate_id.total_pc_unit_cost', 'estimate_id.total_unit_cost','estimate_id.estimate_material_line_ids','estimate_id.estimate_material_line_ids.pcs_unit_divided','estimate_id.estimate_material_line_ids.unit_cost')
    def compute_cost_price(self):
        for rec in self:
           # Calculate the total material cost and services sum total
            total_material_cost, services_sum_total = rec._calculate_material_cost()
            #Calculate teh total cost price
            total_cost_price = total_material_cost + services_sum_total + rec.unit_labor_rate + rec.unit_burden_rate + rec.commission_amt
            
            rec.unit_cost = total_cost_price
        
        _logger.info("compute_cost_price method completed")
    
    
    @api.depends('quantity','profit_margin','estimate_id.bar_unit', 'estimate_id.total_pc_unit_cost', 'estimate_id.total_unit_cost','estimate_id.estimate_material_line_ids')
    def compute_selling_price(self):
        for rec in self:
            # Calculate the total material cost and services sum total
            total_material_cost, services_sum_total = rec._calculate_material_cost()
            
            unit_setup_cost = rec.unit_setup_cost
            total_cycle_rate = rec.estimate_id.total_cycle_rate 
            profit_100 = rec.profit_margin / 100
            #Calculate selling price
            selling_price_total = ((total_material_cost + services_sum_total) + unit_setup_cost + total_cycle_rate) / (1 - profit_100)
            
            rec.selling_price = selling_price_total
        
        _logger.info("compute_selling_price method completed")
        

    @api.depends('selling_price','commission_amt')
    def compute_selling_price_with_commission(self):
        for rec in self:
            rec.selling_price_with_commission = rec.selling_price + rec.commission_amt
        
        _logger.info(" compute_selling_price_with_commission method completed")
              
    @api.depends('selling_price_with_commission')
    def compute_total_job_profit(self):
        for rec in self:
            rec.total_profit = (rec.selling_price_with_commission - rec.unit_cost) * rec.quantity
        _logger.info("compute_total_job_profit method completed")
     
    @api.depends('selling_price','estimate_id.commission_per')
    def compute_commission_amount(self):
        for rec in self:
            rec.commission_amt = (rec.selling_price * rec.estimate_id.commission_per) / 100
        _logger.info("compute_commission_amount method completed")
               
    @api.depends('estimate_id.work_center_ids','quantity','selling_price')
    def compute_hours_to_produce(self):
        for rec in self:
            cycle_hour = rec.estimate_id.total_cycle_time / 60  # Replace with the actual value of H41
            setup_hour = rec.estimate_id.total_setup_time / 60  # Replace with the actual value of H41
            I43 = (cycle_hour / 60) + (setup_hour / 60)  # Replace with the actual value of I43
            C5 = rec.quantity  # Replace with the actual value of C5 (change as needed)

            # Apply the logic from the Excel formula
            if C5 == 1:
                result = I43
            else:
                result = (cycle_hour * (C5 - 1)) + I43
            
            rec.hours_to_produce = result

        _logger.info("compute_hours_to_produce method completed")
        
    @api.depends('quantity','estimate_id.work_center_ids','selling_price')
    def compute_workcenter_rates(self):
        for rec in self:
            initial_labor_rate = rec.estimate_id.initial_labor_rate  # Replace with the actual value of O4
            decrease_rate = rec.estimate_id.decrease_rate  # Replace with the actual value of O5
            min_labor_rate = rec.estimate_id.min_labor_cost  # Replace with the actual value of O6
            quantity_to_produce = rec.quantity  # Replace with the actual value of C6 (change as needed)
            if quantity_to_produce == 1:
                result = initial_labor_rate
            else:
                result = min_labor_rate + (initial_labor_rate - min_labor_rate) * math.exp(-decrease_rate * quantity_to_produce)
            rec.unit_labor_rate = result
        _logger.info("compute_workcenter_rates method completed")

    @api.depends('quantity','estimate_id.work_center_ids','selling_price')
    def compute_setup_unit_cost(self):
        for rec in self:
            if rec.quantity:
                rec.unit_setup_cost = rec.estimate_id.setup_unit_cost / rec.quantity
            else:
                rec.unit_setup_cost = 0
        _logger.info("compute_setup_unit_cost method completed")
              
    @api.depends('quantity','estimate_id.work_center_ids','selling_price')
    def compute_burden_cost(self):
        for rec in self:
            decrease_rate = rec.estimate_id.decrease_rate  # Replace with the actual value of O5
            min_labor_rate = rec.estimate_id.min_labor_cost  # Replace with the actual value of O6
            burden_rate = rec.estimate_id.burden_rate  # Replace with the actual value of O7
            quantity_to_produce = rec.quantity  # Replace with the actual value of C5 (change as needed)
            # Apply the logic from the Excel formula
            if quantity_to_produce == 1:
                result = burden_rate
            else:
                result = min_labor_rate + (burden_rate - min_labor_rate) * math.exp(-decrease_rate * quantity_to_produce)
            rec.unit_burden_rate = result
        _logger.info("compute_burden_cost method completed")

class EstimateMaterialLine(models.Model):
    _name = 'estimate.material.line'
    _description = "Estimate Material Line"
    #CAMBIO ESTO A REQUIRED FALSE AND ONDELETE SET NULL
    product_id = fields.Many2one('product.product', string="Part Number", required=False, ondelete='set null')
    quantity = fields.Float(string="Quantity",default=1)
    unit = fields.Selection([('ea','ea'),('pc','pc')], string="Unit", default='ea',store=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor",store=True)
    unit_cost = fields.Float(string="Unit Cost",store=True)
    unit_price = fields.Float(string="Unit Price",store=True)
    pcs_unit_cost = fields.Float(string="Pcs Unit Cost",compute='_compute_unit_cost', store=True)
    estimate_id = fields.Many2one('customer.estimate', string="Estimate")
    product_type = fields.Selection([('consu', "Goods"),('service', "Service"),('combo', "Combo"),('estimate', "Estimate"),], string="Product Type",store=True)
    rfc_po_id =  fields.Many2one('purchase.order', string='RFQ',store=True) 
    #has_rfc_po = fields.Boolean(compute='_compute_has_rfc_po', store=True, deprecated=True)
    pcs_unit_divided = fields.Float(string="Pc Unit Cost", compute='_compute_pcs_unit_divided', store=True)
    tiered_pricing_ids = fields.One2many('productbreakdown.pricing.line', 'product_id', related='product_id.product_tmpl_id.product_breakdown_pricing_line_ids',  string="Tiered Pricing")
    virtual_available_at_date = fields.Float("Forecasted Qty at Date")
    qty_available_today = fields.Float("Quantity Available Today")
    free_qty_today = fields.Float("Free Quantity Today")
    scheduled_date = fields.Datetime("Scheduled Date")
    forecast_expected_date = fields.Datetime("Forecast Expected Date")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    move_ids = fields.Many2many("stock.move", string="Stock Moves")
    qty_to_deliver = fields.Float("Quantity to Deliver")
    is_mto = fields.Boolean("Make To Order")
    display_qty_widget = fields.Boolean("Display Quantity Widget", compute="_compute_display_qty_widget")

    qty_at_date = fields.Char(string="Quantity at Date", compute="_compute_qty_at_date")

    def _compute_qty_at_date(self):
        for record in self:
            # Set today's date in the format YYYY-MM-DD
            record.qty_at_date = datetime.now().strftime('%Y-%m-%d')
    
    @api.depends('product_id', 'warehouse_id', 'scheduled_date')
    def _compute_display_qty_widget(self):
        for line in self:
            line.display_qty_widget = bool(line.product_id and line.warehouse_id and line.scheduled_date)

    def action_view_detail_forecast(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_forecast_report_action').read()[0]
        action['context'] = {
            'search_default_product_id': self.product_id.id,
            'search_default_warehouse_id': self.warehouse_id.id,
        }
        return action
    
    def _compute_display_qty_widget(self):
        for record in self:
            record.display_qty_widget = bool(record.product_id)
     
    @api.constrains('unit','pricing_uom','product_type')
    def _validate_and_update_estimate_bar_unit(self):
        """
        Enforce the 'pc' unit change on the related estimate model when necessary.
        """
        for record in self:
            _logger.info(f"Checking unit change for product {record.product_id.name} {record.product_type} with unit {record.unit} - {record.unit_cost}")
                    
            # Only update if product type is not 'service'
            if record.product_id and record.product_type != 'service':
                if record.unit == 'pc' and record.estimate_id:
                            # Update bar_unit and pricing_uom to 'pc' when the product type is not 'service'
                    record.estimate_id.pricing_uom = 'pc'
                    record.estimate_id.bar_unit = 'pc'
                else:
                            # If unit is not 'pc', set to 'ea' by default
                    record.estimate_id.pricing_uom = 'ea'
                    record.estimate_id.bar_unit = 'ea'
    

            _logger.info("_validate_and_update_estimate_bar_unit method completed")


       
    @api.depends('unit_cost', 'estimate_id.result_rounded_lowest','unit')
    def _compute_pcs_unit_divided(self):
        """Compute pcs_unit_divided based on unit_cost and the parent estimate's result_rounded_lowest."""
        for record in self:
            if record.unit in ['pc']:
                if record.estimate_id and record.estimate_id.result_rounded_lowest:
                    record.pcs_unit_divided = record.unit_cost / record.estimate_id.result_rounded_lowest
                else:
                    record.pcs_unit_divided = 0.0
            else:
                record.pcs_unit_divided = 0.0
        _logger.info(" _compute_pcs_unit_divided method completed")      
    

    @api.onchange('product_id','unit','product_type')
    def _check_service_unit(self):
        """
        Ensure that products of type 'service' always use 'ea' as the unit.
        """
        if self.product_id and self.product_type == 'service' and self.unit != 'ea':
            self.unit = 'ea'  # Automatically set the unit to 'ea'
            #return {
            #    'warning': {
            #        'title': "Invalid Unit for Service Product",
            #        'message': "The unit for service products must always be 'Each'. It has been reset automatically."
            #    }
            #}
        _logger.info(" _compute_pcs_unit_divided method completed")  
        
 
    @api.constrains('product_id', 'unit','product_type')
    def _validate_service_unit(self):
        """
        Validate that products of type 'service' use 'ea' as the unit.
        """
        for record in self:
            if record.product_type == 'service' and record.unit != 'ea':
                self.unit = 'ea'
                return {
                    'warning': {
                        'title': "Invalid Unit for Service Product",
                        'message': "The unit for service products must always be 'Each'. It has been reset automatically."
                    }
                }
        _logger.info("  _validate_service_unit method completed")     
   
     
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._compute_unit_cost()
        return record

       
    @api.onchange('product_id', 'vendor_id', 'quantity', 'product_type','estimate_id')
    def onchange_product_id(self):
        #if self.product_id and self.vendor_id:
        if self.product_id:
             # Set quantity to 1 if it was not set
            if self.quantity is None or self.quantity == 0:
                self.quantity = 1  # You can change this default if needed
            #RIGHT NOW IS FETCHING THE FIRST VENDOR, NEED TO CHANGE THIS TO FETCH THE VENDOR SELECTED ADN SETTING QUANTITY TO 1 AND UNIT TO EA
            if self.product_id.variant_seller_ids:
                #_logger.info(" self.product_id.variant_seller_ids.read(): %s", self.product_id.variant_seller_ids[0].partner_id.read())
                self.vendor_id = self.product_id.variant_seller_ids[0].partner_id.id
                
                                # Select the vendor based on the product
                if self.vendor_id is None:  # Only set vendor_id if it is not already set
                    self.vendor_id = self.product_id.variant_seller_ids[0].partner_id.id
                 
            tiered_price = self.get_tiered_price(self.product_id.product_tmpl_id)
            
            if tiered_price:
                self.unit_cost = tiered_price
            else:
                 self.unit_cost = self.product_id.standard_price
                 
            _logger.info(f"CHECKING tiered_price {tiered_price} - {self.unit_cost}")
        else:
            # Reset unit cost and quantity if no product_id is selected
            self.unit_cost = 0
            _logger.info(f"CHECKING self.unit_cost ELSE {self.unit_cost}")
            self.quantity = 0  # Reset quantity
        
        _logger.info("onchange_product_id method completed")

   
    def get_tiered_price(self,product_id):
        if product_id:
            applicable_tiers = product_id.product_breakdown_pricing_line_ids.filtered(lambda t: t.quantity <= self.quantity)
            if applicable_tiers:
                return max(applicable_tiers, key=lambda t: t.quantity).price
            else:
                return 5000000
        _logger.info("get_tiered_price method completed")
        return None
    

    @api.depends('estimate_id','product_id', 'vendor_id', 'quantity', 'product_type')
    def _compute_unit_cost(self):
        for record in self:
            if record.product_id:
                tiered_price = record.get_tiered_price(record.product_id)
                if tiered_price:
                    record.unit_cost = tiered_price
                else:
                    record.unit_cost = record.product_id.standard_price
            else:
                record.unit_cost = 0
        _logger.info(" _compute_unit_cost method completed")       
                
class EstimateWorkCenter(models.Model):
    _name = 'estimate.work.center'
    _description = "Work Center (Routing Cost Info)"
    _rec_name = 'workcenter_id'

    workcenter_id = fields.Many2one('workcenter.template', string="Work Center")
    setup_time = fields.Float(string="Setup Time")
    setup_unit = fields.Char(string="Setup Unit", default="M")
    cycle_time = fields.Float(string="Cycle Time")
    cycle_unit = fields.Char(string="Cycle Unit", default="M")
    estimate_id = fields.Many2one('customer.estimate', string="Estimate")
    setup_rate_amt = fields.Float(string="Setup Rate", store=True, compute="compute_work_center_rate" )
    cycle_rate_amt = fields.Float(string="Cycle Rate", store=True, compute="compute_work_center_rate")
    burden_rate_amt = fields.Float(string="Burden Rate", store=True, compute="compute_work_center_rate")
    labor_rate = fields.Float(string="Labor Rate", store=True, compute="compute_work_center_rate")

    @api.depends('workcenter_id','setup_time','cycle_time')
    def compute_work_center_rate(self):
        for rec in self:
            rec.setup_rate_amt = (rec.setup_time * rec.workcenter_id.setup_rate) / 60
            rec.cycle_rate_amt = (rec.cycle_time * rec.workcenter_id.cycle_rate) / 60
            rec.burden_rate_amt = ((rec.setup_time + rec.cycle_time) /60 ) * rec.workcenter_id.burden_rate
            rec.labor_rate = ((rec.setup_time + rec.cycle_time) /60 ) * rec.workcenter_id.labor_rate
        _logger.info("compute_work_center_rate method completed")
        
      
    @api.depends('estimate_id','setup_time', 'cycle_time', 'setup_rate_amt', 'cycle_rate_amt', 'burden_rate_amt', 'labor_rate')
    def update_estimate_totals(self):
        for rec in self:
            if rec.estimate_id:  # Ensure the record has an associated estimate
                # Sum all related records for the same estimate_id
                estimate = rec.estimate_id
                estimate.setup_time_total_wc = sum(estimate.work_center_ids.mapped('setup_time'))
                estimate.cycle_time_total_wc = sum(estimate.work_center_ids.mapped('cycle_time'))
                estimate.setup_rate_amt_total_wc = sum(estimate.work_center_ids.mapped('setup_rate_amt'))
                estimate.cycle_rate_amt_total_wc = sum(estimate.work_center_ids.mapped('cycle_rate_amt'))
                estimate.burden_rate_amt_total_wc = sum(estimate.work_center_ids.mapped('burden_rate_amt'))
                estimate.labor_rate_total_wc = sum(estimate.work_center_ids.mapped('labor_rate'))
        _logger.info("update_estimate_totals method completed")

  
    @api.model
    def create(self, values):
        # Create the EstimateWorkCenter record
        record = super(EstimateWorkCenter, self).create(values)
        
        # Update the totals for the related customer.estimate
        record.update_estimate_totals()
        _logger.info(" def create(self, values) method completed")
        return record
   
    def write(self, values):
        # Write changes to the EstimateWorkCenter record
        result = super(EstimateWorkCenter, self).write(values)
        
        # Update the totals for the related customer.estimate after the update
        for rec in self:
            rec.update_estimate_totals()
        _logger.info(" def create(self, values) method completed")        
        return result