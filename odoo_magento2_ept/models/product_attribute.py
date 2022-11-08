# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
from odoo import models, fields


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    _description = 'Product Attribute'

    magento_attribute_id = fields.Many2one('magento.product.attribute', string='Magento Attribute',
                                           ondelete='cascade')
