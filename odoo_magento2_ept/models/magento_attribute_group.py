# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
from odoo import models, fields
from .api_request import req, create_search_criteria
from ..python_library.php import Php


class MagentoAttributeGroup(models.Model):
    _name = "magento.attribute.group"
    _description = 'Magento Attribute Option'

    name = fields.Char(string="Attribute Group Name",
                       help="Magento Attribute Group Name",
                       required=True)
    instance_id = fields.Many2one(comodel_name='magento.instance',
                                  string='Instance',
                                  ondelete="cascade",
                                  help="This field relocates magento instance")
    attribute_group_id = fields.Char(string="Attribute Group",
                                     help="Magento Attribute Group ID")
    sort_order = fields.Integer(string='Attribute Sort Order', readonly=True)
    attribute_set_id = fields.Many2one(comodel_name='magento.attribute.set',
                                       string="Magento Attribute Set")
    magento_attribute_ids = fields.Many2many(comodel_name='magento.product.attribute',
                                             string='Magento Attribute IDs',
                                             help='Magento Attribute')
    active = fields.Boolean(string="Status", default=True)

    def import_attribute_group(self, instance, attr_set):
        """
        Import Magento Attribute Group in odoo
        :param instance: Magento instance
        :param attr_set: attribute set list
        :return:
        """
        filters = create_search_criteria({'attribute_set_id': int(attr_set.attribute_set_id)})
        query_str = Php.http_build_query(filters)
        url = f"/V1/products/attribute-sets/groups/list?{query_str}"
        groups = req(instance, url)
        for group in groups.get('items', []):
            self.create_attribute_group(instance, attr_set, group)
        return True

    def create_attribute_group(self, instance, attr_set, group):
        """
        check attribute group is found then update else create new.
        """
        group_id = group.get('attribute_group_id', 0)
        m_group = self.search([('attribute_group_id', '=', group_id),
                               ('instance_id', '=', instance.id)], limit=1)
        if not m_group:
            m_group = self.create({
                'attribute_group_id': group_id,
                'name': group.get('attribute_group_name', ''),
                'attribute_set_id': attr_set.id,
                'instance_id': instance.id
            })
        return m_group
