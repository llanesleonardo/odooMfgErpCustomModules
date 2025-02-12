# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPortalQuotation(http.Controller):
#     @http.route('/custom_portal_quotation/custom_portal_quotation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_portal_quotation/custom_portal_quotation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_portal_quotation.listing', {
#             'root': '/custom_portal_quotation/custom_portal_quotation',
#             'objects': http.request.env['custom_portal_quotation.custom_portal_quotation'].search([]),
#         })

#     @http.route('/custom_portal_quotation/custom_portal_quotation/objects/<model("custom_portal_quotation.custom_portal_quotation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_portal_quotation.object', {
#             'object': obj
#         })

