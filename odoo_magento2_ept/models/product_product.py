# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields mapping to Magento products
"""
from odoo import fields, models


class ProductProduct(models.Model):
    """
    Describes fields mapping to Magento products
    """
    _inherit = 'product.product'

    def _compute_magento_product_count(self):
        """
        calculate magento product count
        :return:
        """
        magento_product_obj = self.env['magento.product.product']
        for product in self:
            magento_products = magento_product_obj.search([('odoo_product_id', '=', product.id)])
            product.magento_product_count = len(magento_products) if magento_products else 0

    magento_product_count = fields.Integer(string='# Product Counts',
                                           compute='_compute_magento_product_count')

    def view_magento_products(self):
        """
        This method is used to view Magento product.
        :return: Action
        """
        magento_product_ids = self.mapped('magento_product_ids')
        xmlid = ('odoo_magento2_ept', 'action_magento_stock_picking')
        action = self.env['ir.actions.act_window'].for_xml_id(*xmlid)
        action['domain'] = "[('id','in',%s)]" % magento_product_ids.ids
        if not magento_product_ids:
            return {'type': 'ir.actions.act_window_close'}
        return action

    magento_product_ids = fields.One2many(
        'magento.product.product',
        inverse_name='odoo_product_id',
        string='Magento Products',
        help='Magento Product Ids'
    )

    def write(self, vals):
        """
        This method will archive/unarchive Magento product based on Odoo Product
        :param vals: Dictionary of Values
        """
        if 'active' in vals.keys():
            magento_product_product_obj = self.env['magento.product.product']
            for product in self:
                magento_product = magento_product_product_obj.search(
                    [('odoo_product_id', '=', product.id)])
                if vals.get('active'):
                    magento_product = magento_product_product_obj.search(
                        [('odoo_product_id', '=', product.id), ('active', '=', False)])
                magento_product and magento_product.write({'active': vals.get('active')})
        res = super(ProductProduct, self).write(vals)
        return res
