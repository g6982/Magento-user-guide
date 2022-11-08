# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes Magento Tax Class
"""
from odoo import models, api, fields
from .api_request import req


class MagentoTaxClass(models.Model):
    """
    Describes Magento Tax Class
    """
    _name = 'magento.tax.class'
    _description = 'Magento Tax Class'
    _rec_name = 'magento_tax_class_name'

    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete="cascade",
                                          help="This field relocates magento instance")
    magento_tax_class_id = fields.Char(string='Magento Tax Id', help='Magento Tax Class Id')
    magento_tax_class_name = fields.Char(string='Magento Tax Name', help='Magento Tax Class Name')
    magento_tax_class_type = fields.Char(string='Magento Tax Type', help='Magento Tax Class Type')
    active = fields.Boolean(string="Status", default=True)

    _sql_constraints = [
        ('unique_magento_tax_class_id', 'unique(magento_instance_id,magento_tax_class_id)',
         'This tax class is already exist')]

    def import_magento_tax_class(self, instance):
        """
        This method used for import Tax Classes.
        """
        url = '/V1/taxClasses/search?searchCriteria[page_size]=50&searchCriteria[currentPage]=1'
        tax_class = req(instance, url)
        items = tax_class.get('items', list())
        for item in items:
            self.create_update_magento_tax_class(instance, item)
        return True

    def create_update_magento_tax_class(self, instance, tax_class):
        tax_class_id = tax_class.get('class_id', 0)
        m_tax_class = self.search([
            ('magento_tax_class_id', '=', tax_class_id),
            ('magento_instance_id', '=', instance.id)
        ])
        values = {
            'magento_tax_class_id': tax_class.get('class_id'),
            'magento_tax_class_name': tax_class.get('class_name'),
            'magento_tax_class_type': tax_class.get('class_type'),
            'magento_instance_id': instance.id
        }
        if not m_tax_class:
            m_tax_class = self.create(values)
        else:
            m_tax_class.write(values)
        return m_tax_class
