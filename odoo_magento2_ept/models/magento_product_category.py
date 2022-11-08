# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_request import req


class MagentoProductCategory(models.Model):
    """
        Describes Magento Product Category
    """
    _name = "magento.product.category"
    _description = 'Magento Attribute Option'
    _rec_name = 'complete_category_name'

    @api.depends('name', 'magento_parent_id.complete_category_name')
    def _compute_complete_name(self):
        for category in self:
            category.complete_category_name = category.name
            parent_id = category.magento_parent_id
            if parent_id:
                complete_name = f"{parent_id.complete_category_name} / {category.name}"
                category.complete_category_name = complete_name

    name = fields.Char(string="Name")
    instance_id = fields.Many2one(comodel_name='magento.instance', string='Magento Instance',
                                  ondelete="cascade",
                                  help="This field relocates magento instance")
    category_id = fields.Char(string="Magento ID", help="Magento ID")
    magento_parent_id = fields.Many2one(comodel_name='magento.product.category',
                                        string='Magento Category', ondelete='cascade',
                                        help="Magento Parent Category ID")
    magento_child_ids = fields.One2many(comodel_name='magento.product.category',
                                        inverse_name='magento_parent_id',
                                        string='Magento Child Categories')
    is_anchor = fields.Boolean(
        string='Anchor?', default=True,
        help="The Is Anchor display setting for categories allows a category to 'inherit'"
             " and display all products from its child categories. When Is Anchor is set to 'Yes',"
             " products assigned to child categories will be combined and displayed in the parent "
             "category along with any products directly assigned to it.")
    is_active = fields.Boolean(string='Is Active?',
                               help="Enable the category by choosing Yes for Is Active field.",
                               default=True)
    complete_category_name = fields.Char(string="Category Name", help="Category Name",
                                         compute="_compute_complete_name", recursive=True)
    active = fields.Boolean(string="Status", default=True)

    def get_all_category(self, instance):
        """
        Get Category data dictionary and this dictionary based on create new category.
        :param instance:
        """
        categories = self.get_magento_product_category(instance)
        self.create_magento_category(instance, categories)

    def _get_parent_category(self, instance, category):
        parent_id = category.get('parent_id', 0)
        if parent_id:
            # Search the parent category in magento.product.category
            category = self.search([('category_id', '=', parent_id),
                                    ('instance_id', '=', instance.id)], limit=1)
            if not category:
                # If the parent category are not available at Odoo we are sending that
                # specific category response from Magento.
                # Magento are providing the settings to set the root category by website wise.
                # So, when we call the /V1/Categories api we will not get the root category
                # in the response.
                response = self.get_magento_product_category(instance, parent_id)
                values = self.prepare_category_values(instance, response)
                category = self.create(values)
        return category

    def create_magento_category(self, instance, category):
        """
        Create the category list in odoo
        :param instance: magento.instance object
        :param category: dict categories, If we get multiple categories in the response then
        response will be in list
        :return:
        """
        parent_category = self._get_parent_category(instance, category)
        m_category = self.search([('category_id', '=', category.get('id', 0)),
                                  ('instance_id', '=', instance.id)], limit=1)
        if not m_category:
            if parent_category:
                category.update({'parent_id': parent_category.id})
            values = self.prepare_category_values(instance, category)
            self.create(values)
        else:
            if parent_category:
                category.update({'parent_id': parent_category.id})
            values = self.prepare_category_values(instance, category)
            m_category.write(values)
        if category.get('children_data', []):
            for categ in category.get('children_data'):
                self.create_magento_category(instance, categ)
        return True

    @staticmethod
    def prepare_category_values(instance, category):
        """
        Prepare the category vals
        :param instance: Magento Instance
        :param category: Data
        :return:
        """
        return {
            'category_id': category.get('id', 0),
            'name': category.get('name', ''),
            'magento_parent_id': category.get('parent_id', False),
            'is_active': category.get('is_active', False),
            'instance_id': instance.id
        }

    @staticmethod
    def get_magento_product_category(instance, parent_id=0):
        """
        Get all the Magento product category using API
        :param instance: Instance record
        :param parent_id: Parent magento.product.category id
        :return: dict(category response)
        """
        url = '/V1/categories'
        if parent_id:
            url = f"{url}/{parent_id}"
        try:
            categories = req(instance, url)
        except Exception as error:
            raise UserError(_("Error while requesting Product Category" + str(error)))
        return categories

    def get_categories(self, instance, item):
        links = item.get('extension_attributes', {}).get('category_links', [])
        ids = []
        category = self.env['magento.product.category']
        for link in links:
            ids.append(link.get('category_id'))
        if ids:
            category = self.search([('instance_id', '=', instance.id), ('category_id', 'in', ids)])
        return category.ids
