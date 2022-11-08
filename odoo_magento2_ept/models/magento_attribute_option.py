# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
from odoo import models, fields


class MagentoAttributeOption(models.Model):
    _name = "magento.attribute.option"
    _description = 'Magento Attribute Option'

    name = fields.Char(string='Magento Attribute Value', required=True, translate=True)
    odoo_option_id = fields.Many2one('product.attribute.value', string='Odoo Attribute option',
                                     ondelete='cascade')
    odoo_attribute_id = fields.Many2one('product.attribute', string='Odoo Attribute',
                                        ondelete='cascade')
    magento_attribute_option_name = fields.Char(string="Magento Attribute Option Value",
                                                help="Magento Attribute Value")
    magento_attribute_id = fields.Many2one("magento.product.attribute", string="Magento Attribute",
                                           ondelete='cascade')
    magento_attribute_option_id = fields.Char(string='Magento ID')
    instance_id = fields.Many2one('magento.instance', string="Instance", ondelete="cascade")
    active = fields.Boolean(string="Status", default=True)

    def create_attribute_option(self, attribute, m_attribute, o_attribute):
        for option in attribute.get('options', []):
            option.update({'label': option.get('label').strip()})
            if option.get('label'):
                o_option = self._get_odoo_attribute_value(o_attribute.id, option.get('label'))
                m_option = self.search([('instance_id', '=', m_attribute.instance_id.id),
                                        ('magento_attribute_id', '=', m_attribute.id),
                                        ('odoo_option_id', '=', o_option.id),
                                        ('odoo_attribute_id', '=', o_attribute.id)])
                if not m_option:
                    values = self._prepare_option_value(option, o_option, o_attribute, m_attribute)
                    self.create(values)
        return True

    def _get_odoo_attribute_value(self, attribute_id, label):
        o_option = self.env['product.attribute.value']
        o_option = o_option.search([('name', '=', label),
                                    ('attribute_id', '=', attribute_id)], limit=1)
        if not o_option:
            o_option = o_option.create({'name': label, 'attribute_id': attribute_id})
        return o_option

    @staticmethod
    def _prepare_option_value(option, o_option, o_attribute, m_attribute):
        return {
            'name': option.get('label'),
            'odoo_option_id': o_option.id,
            'odoo_attribute_id': o_attribute.id,
            'magento_attribute_option_id': option.get('value', ''),
            'magento_attribute_id': m_attribute.id,
            'instance_id': m_attribute.instance_id.id,
            'magento_attribute_option_name': option.get('label')
        }
