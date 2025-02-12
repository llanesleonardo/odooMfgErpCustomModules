# -*- coding: utf-8 -*-
# from odoo import http


# class CustomReceiver(http.Controller):
#     @http.route('/custom_receiver/custom_receiver', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_receiver/custom_receiver/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_receiver.listing', {
#             'root': '/custom_receiver/custom_receiver',
#             'objects': http.request.env['custom_receiver.custom_receiver'].search([]),
#         })

#     @http.route('/custom_receiver/custom_receiver/objects/<model("custom_receiver.custom_receiver"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_receiver.object', {
#             'object': obj
#         })

