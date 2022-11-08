# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
import logging
from odoo import models, fields, api, _
from .api_request import req, create_search_criteria
from ..python_library.php import Php

_logger = logging.getLogger(__name__)


class MagentoAttributeSet(models.Model):
    _name = "magento.attribute.set"
    _description = 'Magento Attribute Option'
    _rec_name = 'display_name'

    attribute_set_name = fields.Char(string="Attribute Set Name", help="Magento Attribute Set Name")
    instance_id = fields.Many2one('magento.instance', string='Instance', ondelete="cascade",
                                  help="This field relocates magento instance record")
    attribute_set_id = fields.Char(string="Attribute Set ID", help="Magento Attribute Set ID")
    sort_order = fields.Integer(string='Sort Order')
    attribute_group_ids = fields.One2many('magento.attribute.group', 'attribute_set_id',
                                          string="Attribute group", help="Attribute group")
    active = fields.Boolean(string="Status", default=True)
    display_name = fields.Char(string="Display Name", help="Display Name",
                               compute='_compute_get_display_name')

    def _compute_get_display_name(self):
        for attr_set in self:
            attr_set.display_name = "{} - {}".format(attr_set.attribute_set_name,
                                                     attr_set.instance_id.name)

    def import_attribute_set(self, instance):
        """
        Import Attribute set in odoo
        :param instance: Magento Instance
        :return:
        """
        # attr_group = self.env['magento.attribute.group']
        m_attribute = self.env['magento.product.attribute']
        filters = create_search_criteria({'entity_type_id': {'gt': -1}})
        query_str = Php.http_build_query(filters)
        url = "/V1/products/attribute-sets/sets/list?{}".format(query_str)
        attr_sets = req(instance, url)
        attr_sets = self.create_attribute_set(instance, attr_sets)
        # for attr_set in attr_sets.get('items', []):
            # m_attr_set = Self Object/Magento Attribute Set
            # attr_group.import_attribute_group(instance, m_attr_set)
        m_attribute.import_magento_attributes(instance, attr_sets)
        return True

    def create_attribute_set(self, instance, attr_sets):
        """
        Check Attributes if not found then create new attributes.
        :param instance: Magento Instance
        :param attr_sets: single import attributes set (type = dict)
        :return: attributes set object
        """
        for attr_set in attr_sets.get('items', []):
            set_id = attr_set.get('attribute_set_id', 0)
            m_attr_set = self.search([('attribute_set_id', '=', set_id),
                                      ('instance_id', '=', instance.id)], limit=1)
            if not m_attr_set:
                m_attr_set = self.create({
                    'attribute_set_name': attr_set.get('attribute_set_name', ''),
                    'attribute_set_id': set_id,
                    'instance_id': instance.id,
                    'sort_order': attr_set.get('sort_order', 0)
                })
            attr_set.update({'set_id': m_attr_set.id})
        return attr_sets
