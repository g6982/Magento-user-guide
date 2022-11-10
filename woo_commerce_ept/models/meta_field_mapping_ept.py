# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger("WooCommerce")


class WooMetaFieldMappingEpt(models.Model):
    _name = "woo.meta.mapping.ept"
    _description = "WooCommerce Meta Field Mapping"

    woo_meta_key = fields.Char('WooCommerce Meta Key')
    woo_operation = fields.Selection([
        ('import_product', 'Import Products'),
        ('import_customer', 'Import Customers'),
        ('import_unshipped_orders', 'Import Unshipped Orders'),
        ('import_completed_orders', 'Import Shipped Orders'),
        ('is_update_order_status', "Export Shippment Infomation / Update Order Status")], 'WooCommerce Operation')
    model_id = fields.Many2one('ir.model')
    field_id = fields.Many2one('ir.model.fields')
    instance_id = fields.Many2one("woo.instance.ept", copy=False, ondelete="cascade")

    _sql_constraints = [
        ('_meta_mapping_unique_constraint', 'unique(woo_meta_key,instance_id,woo_operation,model_id)',
         'WooCommerce Meta Key, WooCommerce Operation and Model must be unique in the Meta Mapping '
         'as per WooCommerce Instance.')]

    def get_model_domain(self):
        model_name_list = ['res.partner', 'sale.order', 'stock.picking']
        data_dict = {
            'import_product': ['product.template', 'product.product'],
            'import_customer': model_name_list[:1],
            'import_unshipped_orders': model_name_list,
            'import_completed_orders': model_name_list,
            'is_update_order_status': model_name_list[1:],
        }
        return data_dict

    @api.onchange('woo_operation')
    def _onchange_operation(self):
        model_list = self.get_model_domain().get(self.woo_operation)
        return {'domain': {'model_id': [('model', 'in', model_list)]}}
