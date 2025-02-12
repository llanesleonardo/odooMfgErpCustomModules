# -*- coding: utf-8 -*-

from odoo import models, fields, api


class custom_receiver(models.Model):
     _name = 'custom_receiver.custom_receiver'
     _description = 'custom_receiver.custom_receiver'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

