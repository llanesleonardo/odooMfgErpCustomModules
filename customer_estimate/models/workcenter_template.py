# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command


class WorkcenterTemplate(models.Model):
    _name = 'workcenter.template'
    _description = "Workcenter Template"

    name = fields.Char(string="Name", required=True)
    setup_time = fields.Float(string="Setup Time")
    cycle_time = fields.Float(string="Cycle Time")
    setup_rate = fields.Float(string="Setup Rate")
    cycle_rate = fields.Float(string="Cycle Rate")
    burden_rate = fields.Float(string="Burden Rate")
    labor_rate = fields.Float(string="Labor Rate")