# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
import logging
from odoo import models, fields
from .api_request import req

_logger = logging.getLogger("MagentoEPT")
attr_types = ['textarea', 'text', 'date', 'boolean', 'multiselect', 'price', 'weee', 'weight',
              'media_image', 'select', 'swatch_visual', 'swatch_text']


class MagentoProductAttribute(models.Model):
    """
        Describes Magento Product Attribute
    """
    _name = "magento.product.attribute"
    _rec_name = 'magento_attribute_code'
    _description = 'Magento Product Attribute'

    name = fields.Char('Magento Attribute', required=True, translate=True)
    odoo_attribute_id = fields.Many2one(comodel_name='product.attribute', required=False,
                                        string='Odoo Attributes', ondelete='cascade')
    instance_id = fields.Many2one('magento.instance', string="Instance", ondelete="cascade", )
    magento_attribute_id = fields.Char(string="Magento Id")
    magento_attribute_code = fields.Char(string='Attribute Code', required=False, size=200)
    scope = fields.Selection([('store', 'store'), ('website', 'website'), ('global', 'global')],
                             string='Scope', default='global', required=False)
    frontend_label = fields.Char(string='Label', required=False, size=100)
    position = fields.Integer(string='Positions')
    group_id = fields.Integer(string='Group')
    default_value = fields.Char(string='Default', size=10)
    note = fields.Char(string='Notes', size=200)
    option_ids = fields.One2many('magento.attribute.option', 'magento_attribute_id',
                                 string='Options')
    attribute_type = fields.Selection([
        ('char', 'Char'), ('text', 'Text'), ('select', 'Select'),
        ('multiselect', 'Multiselect'), ('boolean', 'Boolean'), ('integer', 'Integer'),
        ('date', 'Date'), ('datetime', 'Datetime'), ('binary', 'Binary'), ('float', 'Float')
    ], string='Type Of Attribute', required=False)
    active = fields.Boolean(string="Status", default=True)

    def import_magento_attributes(self, instance, attr_sets, is_raise=False):
        """
        Import Attributes from Magento to Odoo.
        :param instance: Magento Instance object
        :param attr_sets:  magento attribute set dictionary
        :param is_raise: To raise the error message while importing attribute sets
        :return:
        """
        option = self.env['magento.attribute.option']
        for attr_set in attr_sets.get('items', []):
            url = f"/V1/products/attribute-sets/{attr_set.get('attribute_set_id')}/attributes"
            attributes = req(instance, url, method='GET', is_raise=is_raise)
            for attribute in attributes:
                if attribute.get('options', []):
                    # We have added this condition for identify only those attributes which have
                    # any attribute value set. Because, we can not create variant product without
                    # attribute options.
                    self.__update_attribute_type(attribute)
                    m_attribute = self._search_layer_attribute(attribute, instance)
                    o_attribute = self._search_odoo_attribute(attribute, m_attribute)
                    m_attribute.write({'odoo_attribute_id': o_attribute.id})
                    option.create_attribute_option(attribute, m_attribute, o_attribute)
        return True

    def _search_layer_attribute(self, attribute, instance):
        m_attribute = self.search([('magento_attribute_id', '=', attribute.get('attribute_id')),
                                   ('magento_attribute_code', '=', attribute.get('attribute_code')),
                                   ('instance_id', '=', instance.id)], limit=1)
        if not m_attribute:
            m_attribute = self.create_layer_attribute(attribute, instance)
        return m_attribute

    def create_layer_attribute(self, attribute, instance):
        values = self._prepare_layer_attribute_values(attribute, instance)
        return self.create(values)

    @staticmethod
    def _prepare_layer_attribute_values(attribute, instance):
        return {
            'instance_id': instance.id,
            'magento_attribute_id': attribute.get('attribute_id'),
            'name': attribute.get('default_frontend_label', 'No frontend label'),
            'magento_attribute_code': attribute.get('attribute_code'),
            'scope': attribute.get('scope'),
            'attribute_type': attribute.get('layer_type'),
            'frontend_label': attribute.get('default_frontend_label'),
            'default_value': attribute.get('default_value')
        }

    def _search_odoo_attribute(self, attribute, m_attribute):
        p_attribute = self.env['product.attribute']
        p_attribute = p_attribute.search([('magento_attribute_id', '=', m_attribute.id)])
        if not p_attribute:
            p_attribute = p_attribute.search([
                ('name', '=', attribute.get('default_frontend_label')),
                ('magento_attribute_id', '=', False)], limit=1)
            if not p_attribute:
                p_attribute = self.create_attribute(attribute, m_attribute.id)
        return p_attribute

    def create_attribute(self, attribute, magento_id):
        p_attribute = self.env['product.attribute']
        values = self._prepare_attribute_value(attribute, magento_id)
        return p_attribute.create(values)

    @staticmethod
    def _prepare_attribute_value(attribute, magento_id):
        return {
            'name': attribute.get('default_frontend_label', ''),
            'create_variant': 'always',
            'display_type': attribute.get('odoo_type'),
            'magento_attribute_id': magento_id
        }

    @staticmethod
    def __update_attribute_type(attribute):
        odoo_type = 'radio'
        layer_type = 'text'
        input_type = attribute.get('frontend_input', '')
        if input_type in attr_types:
            if input_type in ['select', 'multiselect']:
                odoo_type = 'select'
            elif input_type == 'textarea':
                layer_type = 'text'
            elif input_type in ['swatch_visual', 'swatch_text', 'swatch_text']:
                odoo_type = 'color'
                layer_type = 'select'
            elif input_type in ['price', 'weee', 'weight']:
                layer_type = 'float'
            elif input_type == 'text':
                layer_type = 'char'
            elif input_type == 'media_image':
                layer_type = 'binary'
            else:
                layer_type = attribute.get('frontend_input')
        attribute.update({'odoo_type': odoo_type, 'layer_type': layer_type})
        return True

    def search_attribute_by_value(self, instance, attribute, set_id):
        m_option = self.env['magento.attribute.option']
        m_attribute = self.search([('name', '=ilike', attribute.get('label')),
                                   ('instance_id', '=', instance.id)], limit=1)
        if not m_attribute:
            sets = self.__prepare_sets(set_id)
            _logger.info("Importing product attributes by attribute set ID...")
            self.import_magento_attributes(instance, sets)
            # We are again searching the attribute by its name if the attribute found then we will
            # search the proper value
            m_attribute = self.search([('name', '=ilike', attribute.get('label')),
                                       ('instance_id', '=', instance.id)], limit=1)
        if attribute:
            m_option = self._search_attribute_value(attribute, m_attribute, instance, set_id)
        return {
            'value_id': m_option.odoo_option_id.id,
            'attribute_id': m_attribute.odoo_attribute_id.id,
            'm_value_id': m_option.id,
            'm_attribute_id': m_attribute.id
        }

    @staticmethod
    def __prepare_sets(set_id):
        return {
            'items': [
                {
                    'attribute_set_id': set_id
                }
            ]
        }

    def _search_attribute_value(self, attribute, m_attribute, instance, set_id):
        option = self.env['magento.attribute.option']
        if not attribute.get('value', False):
            return option
        option = option.search([('magento_attribute_id', '=', m_attribute.id),
                                ('magento_attribute_option_name', '=', attribute.get('value'))],
                               limit=1)
        if not option:
            sets = self.__prepare_sets(set_id)
            _logger.info("Attribute value is not found...")
            _logger.info("Importing product attributes by attribute set ID...")
            self.import_magento_attributes(instance, sets)
        return option

    def open_attribute_value(self):
        """
        This method used for smart button for view all attribute value.
        :return:
        """
        return {
            'name': 'Attribute Value',
            'type': 'ir.actions.act_window',
            'res_model': 'magento.attribute.option',
            'view_mode': 'tree,form',
            'domain': [('magento_attribute_id', '=', self.id)]
        }
