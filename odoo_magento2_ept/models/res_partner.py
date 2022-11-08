# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_magento_customer = fields.Boolean(string="Is Magento Customer?",
                                         help="Used for identified that the customer is imported "
                                              "from Magento store.")
    magento_instance_id = fields.Many2one('magento.instance', string='Instance',
                                          help="This field relocates magento instance")
    magento_res_partner_ids = fields.One2many(comodel_name="magento.res.partner.ept",
                                              inverse_name="partner_id",
                                              string='Magento Customers',
                                              help='This relocates Magento Customers')
