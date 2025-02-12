# -*- coding: utf-8 -*-
# from odoo import http


# class CustomMftopo(http.Controller):
#     @http.route('/custom_mftopo/custom_mftopo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_mftopo/custom_mftopo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_mftopo.listing', {
#             'root': '/custom_mftopo/custom_mftopo',
#             'objects': http.request.env['custom_mftopo.custom_mftopo'].search([]),
#         })

#     @http.route('/custom_mftopo/custom_mftopo/objects/<model("custom_mftopo.custom_mftopo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_mftopo.object', {
#             'object': obj
#         })

