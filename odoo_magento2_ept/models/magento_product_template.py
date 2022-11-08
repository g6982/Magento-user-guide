# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields and methods for Magento products templates
"""
import os
import logging
import json
import codecs
import io
from datetime import datetime
from PIL import Image
from odoo import models, fields, api
from .api_request import req
from ..python_library.php import Php

_logger = logging.getLogger("MagentoEPT")


class MagentoProductTemplate(models.Model):
    """
    Describes fields and methods for Magento products templates
    """
    _name = 'magento.product.template'
    _description = 'Magento Product Template'
    _rec_name = "magento_product_name"

    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete="cascade",
                                          help="This field relocates magento instance")
    magento_product_template_id = fields.Char(string="Magento Product Id",
                                              help="Magento Product Id")
    magento_product_name = fields.Char(string="Magento Product Name", help="Magento Product Name",
                                       translate=True)
    odoo_product_template_id = fields.Many2one(comodel_name='product.template', ondelete='restrict',
                                               string="Odoo Product Template", required=True)
    magento_product_ids = fields.One2many(comodel_name='magento.product.product',
                                          inverse_name='magento_tmpl_id',
                                          string="Magento Products", help="Magento Products")
    magento_website_ids = fields.Many2many('magento.website', string='Magento Websites',
                                           readonly=False, help='Magento Websites',
                                           domain="[('magento_instance_id','=',magento_instance_id)]")
    created_at = fields.Date(string='Product Created At',
                             help="Date when product created into Magento")
    updated_at = fields.Date(string='Product Updated At',
                             help="Date when product updated into Magento")
    product_type = fields.Selection(
        [('simple', 'Simple Product'), ('configurable', 'Configurable Product'),
         ('virtual', 'Virtual Product'), ('downloadable', 'Downloadable Product'),
         ('group', 'Group Product'), ('bundle', 'Bundle Product'),
         ], string='Magento Product Type', help='Magento Product Type', default='simple')
    magento_sku = fields.Char(string="Magento Product SKU", help="Magento Product SKU")
    description = fields.Text(string="Product Description", help="Description", translate=True)
    short_description = fields.Text(string='Product Short Description', help='Short Description',
                                    translate=True)
    magento_product_image_ids = fields.One2many(comodel_name='magento.product.image',
                                                inverse_name='magento_tmpl_id',
                                                string="Magento Product Images",
                                                help="Magento Product Images")
    # NOT USED
    # magento_product_price = fields.Float(
    #     string="Magento Product Prices",
    #     help="Magento Product Price"
    # )
    sync_product_with_magento = fields.Boolean(string='Sync Product with Magento',
                                               help="If Checked means, Product synced With "
                                                    "Magento Product")
    active_template = fields.Boolean(string='Odoo Template Active',
                                     related="odoo_product_template_id.active")
    active = fields.Boolean(string="Active", default=True)
    image_1920 = fields.Image(related="odoo_product_template_id.image_1920")
    total_magento_variants = fields.Integer(string="Total Variants",
                                            compute='_compute_total_magento_variant')
    list_price = fields.Float(string='Sales Price', related='odoo_product_template_id.list_price',
                              readonly=False, digits='Product Price')
    standard_price = fields.Float(string='Cost', related='odoo_product_template_id.standard_price',
                                  readonly=False, digits='Product Price')
    attribute_line_ids = fields.One2many(related='odoo_product_template_id.attribute_line_ids')
    currency_id = fields.Many2one(related='odoo_product_template_id.currency_id')
    category_ids = fields.Many2many("magento.product.category", string="Categories",
                                    help="Magento Categories")
    attribute_set_id = fields.Many2one('magento.attribute.set', string='Attribute Set',
                                       help="Magento Attribute Sets")
    export_product_to_all_website = fields.Boolean(string="Export product to all website?",
                                                   help="If checked, product will be exported for "
                                                        "all websites otherwise export for the "
                                                        "selected websites")
    magento_tax_class = fields.Many2one(comodel_name='magento.tax.class', string='Tax Class',
                                        help="Magento Tax Class")

    _sql_constraints = [('_magento_template_unique_constraint',
                         'unique(magento_sku,magento_instance_id,magento_product_template_id)',
                         "Magento Product Template must be unique")]

    @api.depends('magento_product_ids.magento_tmpl_id')
    def _compute_total_magento_variant(self):
        for template in self:
            # do not pollute variants to be prefetched when counting variants
            template.total_magento_variants = len(template.with_prefetch().magento_product_ids)

    def write(self, vals):
        """
        This method use to archive/un-archive Magento product variants base on Magento product templates.
        :param vals: dictionary for template values
        :return: res
        """
        res = super(MagentoProductTemplate, self).write(vals)
        if (vals.get('active') and len(self.magento_product_ids) == 0) or (
                'active' in vals and not vals.get('active')):
            self.with_context(active_test=False).mapped('magento_product_ids').write(
                {'active': vals.get('active')})
        return res

    def view_odoo_product_template(self):
        """
        This method id used to view odoo product template.
        :return: Action
        """
        if self.odoo_product_template_id:
            return {
                'name': 'Odoo Product',
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', '=', self.odoo_product_template_id.id)],
            }
        return True

    def __search_layer_template(self, line, item, values):
        template = self.search([('magento_instance_id', '=', line.instance_id.id),
                                '|', ('magento_product_template_id', '=', item.get('id')),
                                ('magento_sku', '=', item.get('sku'))], limit=1)
        if not template:
            template = self.search([('magento_instance_id', '=', line.instance_id.id),
                                    '|', ('magento_product_template_id', '=', item.get('id')),
                                    ('magento_sku', '=', item.get('sku')), ('active', '=', False)], limit=1)
            template.write({'active': True})

        if not template:
            template = self.env['magento.product.product'].search([('magento_sku', '=', item.get('sku')),
                                                                   ('magento_instance_id', '=',
                                                                    line.instance_id.id)]).magento_tmpl_id
        if not template:
            if item.get('extension_attributes').get('child_products'):
                template = self.env['magento.product.product'].search([('magento_sku', '=',
                                                                        item.get('extension_attributes').get(
                                                                            'child_products')[0].get('simple_product_sku')),
                                                                       ('magento_instance_id', '=',
                                                                        line.instance_id.id)]).magento_tmpl_id
        if template:
            if 'is_order' not in list(self.env.context.keys()):
                if not line.do_not_update_existing_product:
                    template.write(values)
        else:

            template = self.create(values)
        return template

    def create_configurable_template(self, line, item, template):
        instance = line.instance_id
        self.env['magento.product.product'].update_custom_option(item)
        data = self.get_website_category_attribute_tax_class(item, instance)
        values = self.__prepare_template_values(instance, item, data, template=template)
        template = self.__search_layer_template(line, item, values)
        is_verify = self._create_configurable_variant(line, item, template, data)
        if not is_verify:
            return is_verify
        if instance.allow_import_image_of_products:
            # We will only update/create image in layer and odoo product if customer has
            # enabled the configuration from instance.
            images = self.get_product_images(item, data, line)
            self.create_layer_image(instance, images, template=template)
        return template

    def _create_configurable_variant(self, line, item, m_template, data):
        o_template = m_template.odoo_product_template_id
        e_attributes = item.get('extension_attributes', dict())
        is_verify = self._verify_attribute_count(line, item, o_template, e_attributes)
        if is_verify:
            instance = m_template.magento_instance_id
            m_attribute = self.env['magento.product.attribute']
            for product in e_attributes.get('child_products', list()):
                for attribute in product.get('simple_product_attribute', list()):
                    attribute_dict = m_attribute.search_attribute_by_value(instance, attribute,
                                                                           item.get(
                                                                               'attribute_set_id'))
                    self.__add_variant(o_template, attribute_dict)
                    attribute.update(attribute_dict)
            o_template._create_variant_ids()
            child_products = item.get('extension_attributes', dict()).get('child_products', list())
            self._update_variant_sku(line, m_template, item, child_products, data)
        return is_verify

    def _verify_attribute_count(self, line, item, o_template, e_attributes):
        o_attr_count = len(o_template.attribute_line_ids)
        m_attr_count = len(e_attributes.get('attributes'))
        if o_attr_count > 0 and o_attr_count != m_attr_count:
            field_name = 'import_product_queue_line_id'
            if 'is_order' in list(self.env.context.keys()):
                field_name = 'magento_order_data_queue_line_id'
            message = f"Product {item.get('sku')} having mismatch Attribute count. \n" \
                      f"Product having {m_attr_count} attribute at magento side " \
                      f"and {o_attr_count} Attribute at odoo side."
            line.queue_id.log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': message,
                    field_name: line.id
                })]
            })
            return False
        return True

    def _map_variant_in_layer(self, variant, m_template, child, data, item):
        m_product = self.env['magento.product.product']
        instance = m_template.magento_instance_id
        m_id = child.get('simple_product_id')
        m_sku = child.get('simple_product_sku')
        m_product = m_product.search([('magento_instance_id', '=', instance.id),
                                      ('magento_tmpl_id', '=', m_template.id),
                                      ('odoo_product_id', '=', variant.id),
                                      '|',('magento_product_id', '=', m_id), ('magento_sku', '=', m_sku)], limit=1)
        values = self._prepare_variant_value(variant, m_template, child, data, item)
        if m_product:
            values.pop('magento_product_id')
            m_product.write(values)
        else:
            m_product.create(values)
        return True

    def _prepare_variant_value(self, variant, m_template, child, data, item):
        m_product = self.env['magento.product.product']
        values = {
            'odoo_product_id': variant.id,
            'magento_instance_id': m_template.magento_instance_id.id,
            'magento_product_id': child.get('simple_product_id'),
            'magento_sku': child.get('simple_product_sku'),
            'magento_product_name': child.get('product_name'),
            'magento_tmpl_id': m_template.id,
            'created_at': datetime.strptime(item.get('created_at'), '%Y-%m-%d %H:%M:%S').date(),
            'updated_at': datetime.strptime(item.get('created_at'), '%Y-%m-%d %H:%M:%S').date(),
            'product_type': child.get('product_type', 'simple'),
            'magento_website_ids': [(6, 0, data.get('website'))],
            'sync_product_with_magento': True
        }
        description = m_product.prepare_description(item, is_layer=True)
        if description:
            values.update(description)
        return values

    def _update_variant_sku(self, line, m_template, item, child_products, data):
        o_template = m_template.odoo_product_template_id
        variants = self.env['product.product'].search([('product_tmpl_id', '=', o_template.id)])
        for variant in variants:
            value_ids = variant.product_template_variant_value_ids
            child = self.__find_child(value_ids, child_products)
            if child:
                variant.write({
                    'default_code': child.get('simple_product_sku', '')
                })
                self._map_variant_in_layer(variant, m_template, child, data, item)
                prices = child.get('website_wise_product_price_data', list())
                if 'is_order' not in list(self.env.context.keys()):
                    if not line.do_not_update_existing_product and variant:
                        self.update_price_list(line, variant, prices)
        return True

    @staticmethod
    def __find_child(value_ids, child_products):
        value_ids = value_ids.mapped('product_attribute_value_id').ids
        for child in child_products:
            child_values = list()
            for attribute in child.get('simple_product_attribute'):
                child_values.append(attribute.get('value_id'))
            child_values.sort()
            value_ids.sort()
            if len(child_values) == len(value_ids) and child_values == value_ids:
                return child
        return dict()

    def __add_variant(self, template, data):
        line = self.env['product.template.attribute.line']
        line = line.search([('product_tmpl_id', '=', template.id),
                            ('attribute_id', '=', data.get('attribute_id'))])
        value_id = data.get('value_id')
        if value_id:
            if not line:
                line.create({
                    'product_tmpl_id': template.id,
                    'attribute_id': data.get('attribute_id'),
                    'value_ids': [(4, value_id)]
                })
            elif value_id not in line.value_ids.ids:
                line.write({
                    'value_ids': [(4, value_id)]
                })
        return True

    def update_layer_template(self, line, item, product):
        return self.create_template(line, item, product)

    def create_template(self, line, item, product):
        instance = line.instance_id
        data = self.get_website_category_attribute_tax_class(item, instance)
        values = self.__prepare_template_values(instance, item, data, product=product)
        template = self.__search_layer_template(line, item, values)
        if instance.allow_import_image_of_products:
            # We will only update/create image in layer and odoo product if customer has
            # enabled the configuration from instance.
            images = self.get_product_images(item, data, line)
            self.create_layer_image(instance, images, template=template)
        return template

    def create_layer_image(self, instance, images, template=False, variant=False):
        sequence = 0
        for image in images:
            types = image.get('types', list())
            if 'image' in types:
                sequence = 0
            else:
                sequence += 1
            if template:
                odoo_template = template.odoo_product_template_id
                if 'image' in types and not odoo_template.image_1920:
                    odoo_template.write({'image_1920': image.get('image_binary')})
                c_image = self._search_common_image(image, template_id=odoo_template.id)
                self._search_layer_image(image, instance_id=instance.id, c_image_id=c_image.id,
                                         template_id=template.id, sequence=sequence)
            elif variant:
                odoo_variant = variant.odoo_product_id
                c_image = self._search_common_image(image, variant_id=odoo_variant.id)
                self._search_layer_image(image, instance_id=instance.id, c_image_id=c_image.id,
                                         variant_id=variant.id, sequence=sequence)
        return True

    def _search_layer_image(self, image, **kwargs):
        m_image = self.env['magento.product.image']
        domain = [
            ('magento_instance_id', '=', kwargs.get('instance_id')),
            ('magento_image_id', '=', image.get('id'))
        ]
        if 'image' in image.get('types', list()):
            domain.append(('sequence', '=', 0))
        if kwargs.get('template_id', False):
            domain.append(('magento_tmpl_id', '=', kwargs.get('template_id')))
        elif kwargs.get('variant_id', False):
            domain.append(('magento_product_id', '=', kwargs.get('variant_id')))
        m_image = m_image.search(domain)
        if not m_image:
            m_image = self.__create_layer_image(image, **kwargs)
        return m_image

    def __create_layer_image(self, image, **kwargs):
        m_image = self.env['magento.product.image']
        return m_image.create({
            'name': os.path.basename(image.get('file')),
            'odoo_image_id': kwargs.get('c_image_id', False),
            'magento_instance_id': kwargs.get('instance_id', False),
            'magento_image_id': image.get('id'),
            'magento_product_id': kwargs.get('variant_id', False),
            'magento_tmpl_id': kwargs.get('template_id'),
            'sequence': kwargs.get('sequence'),
            'url': image.get('full_path'),
        })

    def _search_common_image(self, image, template_id=False, variant_id=False):
        c_image = self.env['common.product.image.ept']
        domain = list()
        is_match = True
        if template_id:
            domain.append(('template_id', '=', template_id))
        if variant_id:
            domain.append(('product_id', '=', variant_id))
        # We will search the image with url in the common product image.
        # If the image is found then we verify the binary data of that image.
        # If that image is not same then we will update that image.
        # Otherwise, we will create new image record in layer as well.
        c_images = c_image.search(domain)
        # We will map the binary data if we found the image with name.
        for c_image in c_images:
            if c_image.image == image.get('image_binary'):
                return c_image
            is_match = False
        if not is_match or not c_image:
            c_image = self.__create_common_image(template_id, variant_id, image)
        return c_image

    def __create_common_image(self, template_id, variant_id, image):
        c_image = self.env['common.product.image.ept']
        return c_image.create({
            'name': os.path.basename(image.get('file')),
            'url': image.get('full_path'),
            'template_id': template_id,
            'product_id': variant_id,
            'image': image.get('image_binary')
        })

    def get_website_category_attribute_tax_class(self, item, instance):
        m_set = self.env['magento.attribute.set']
        category = self.env['magento.product.category']
        website = self.env['magento.website']
        tax_class = self.env['magento.tax.class']
        attribute = item.get('custom_attributes')
        m_set = m_set.search([('attribute_set_id', '=', item.get('attribute_set_id')),
                              ('instance_id', '=', instance.id)], limit=1)
        websites = item.get('extension_attributes', dict()).get('website_ids', list())
        if websites:
            website = website.search([('magento_instance_id', '=', instance.id),
                                      ('magento_website_id', 'in', websites)])
        categories = category.get_categories(instance, item)
        tax_class = tax_class.search([('magento_instance_id', '=', instance.id),
                                      ('magento_tax_class_id', '=', attribute.get('tax_class_id'))])
        if not m_set and instance.auto_create_product:
            _logger.info("Sending request to import the attribute set by ID..")
            m_set.import_attribute_set(instance)
            # Search attribute set again after importing the attribute set
            m_set = m_set.search([('attribute_set_id', '=', item.get('attribute_set_id')),
                                  ('instance_id', '=', instance.id)], limit=1)
        if not tax_class and instance.auto_create_product:
            # If tax_class is not found then we are creating it when import product.
            tax_class.import_magento_tax_class(instance)
        return {
            'website': website.ids,
            'attribute_set': m_set.id,
            'category': categories,
            'tax_class': tax_class.id
        }

    def get_product_images(self, item, data, line):
        instance = line.instance_id
        log = line.queue_id.log_book_id
        store = self.env['magento.storeview']
        common_image = self.env['common.product.image.ept']
        store = store.search([('magento_website_id', 'in', data.get('website'))], limit=1)
        base_url = store.base_media_url
        if base_url:
            self.__update_path(item, base_url)
            for image in item.get('media_gallery_entries', list()):
                image_binary = False
                verify = instance.magento_verify_ssl
                try:
                    image_binary = common_image.get_image_ept(image.get('full_path', ''), verify=verify)
                except Exception as error:
                    _logger.error(error)
                    message = "{} " \
                              "\nCan't find image." \
                              "\nPlease provide valid Image URL.".format(item.get('full_path'))
                    instance.create_log_line(message=message, model=self._name,
                                             res_id=line.queue_id.id,
                                             log_id=log.id, order_ref=item.get('increment_id', ''))
                if image_binary:
                    image.update({'image_binary': image_binary})
        return item.get('media_gallery_entries', list())

    @staticmethod
    def __update_path(item, base_url):
        for image in item.get('media_gallery_entries', list()):
            image.update({
                'full_path': "{}{}{}".format(base_url, 'catalog/product', image.get('file', ''))
            })
        return True

    def __prepare_template_values(self, instance, item, data, product=False, template=False):
        values = {
            'magento_product_name': item.get('name'),
            'magento_instance_id': instance.id,
            'magento_sku': item.get('sku'),
            'magento_product_template_id': item.get('id'),
            'created_at': datetime.strptime(item.get('created_at'), '%Y-%m-%d %H:%M:%S').date(),
            'updated_at': datetime.strptime(item.get('updated_at'), '%Y-%m-%d %H:%M:%S').date(),
            'product_type': item.get('type_id'),
            'attribute_set_id': data.get('attribute_set'),
            'magento_website_ids': [(6, 0, data.get('website'))],
            'category_ids': [(6, 0, data.get('category'))],
            'magento_tax_class': data.get('tax_class'),
            'sync_product_with_magento': True
        }
        if product:
            values.update({'odoo_product_template_id': product.product_tmpl_id.id})
        elif template:
            values.update({'odoo_product_template_id': template.id})
        description = self.env['magento.product.product'].prepare_description(item, is_layer=True)
        if description:
            values.update(description)
        return values

    def update_price_list(self, line, product, prices):
        website = self.env['magento.website']
        instance = line.instance_id
        # If customer has not selected the "do_not_update_existing_product"
        # It means that we have to update the product price list.
        # for price in item.get('website_wise_product_price_data'):
        for price in prices:
            if instance.catalog_price_scope == 'global':
                instance.pricelist_id.set_product_price_ept(product.id, price.get('price'),
                                                            min_qty=1)
            else:
                website = website.search([('magento_instance_id', '=', instance.id),
                                          ('magento_website_id', '=', price.get('website_id'))],
                                         limit=1)
                self.__set_price_list_item(product, price, website)
        return True

    @staticmethod
    def __set_price_list_item(product, price, website):
        price_lists = website.pricelist_ids.filtered(
            lambda p: p.currency_id.name == price.get('default_store_currency'))
        cost_price_list = website.cost_pricelist_id.filtered(
            lambda p: p.currency_id.name == price.get('default_store_currency'))
        for price_list in price_lists:
            price_list.set_product_price_ept(product.id, price.get('price'), min_qty=1)
        if cost_price_list and price.get('cost_price'):
            cost_price_list.set_product_price_ept(product.id, price.get('cost_price'), min_qty=1)
        return True

    def prepare_attribute_line_data(self, configurable_options):
        """
        This method is used to prepare attribute line  for set attribute line ids in template.
        :param configurable_options: Configurable product attributes options
        :return: Dictionary of Attribute values
        """
        attrib_line_vals = []
        attribute_line_ids_data = False
        if configurable_options:
            for option in configurable_options:
                attribute_data = json.loads(option)
                if attribute_data.get('frontend_label'):
                    odoo_attribute = self.env['product.attribute'].get_attribute(
                        attribute_data.get('frontend_label'),
                        create_variant='always',
                        auto_create=True
                    )
                    attr_val_ids = []
                    for option_values in attribute_data.get('opt_values'):
                        attrib_value = self.find_odoo_attribute_value_id(odoo_attribute,
                                                                         option_values)
                        attr_val_ids.append(attrib_value.id)
                    attribute_line_ids_data = (
                        0, 0, {'attribute_id': odoo_attribute.id, 'value_ids': attr_val_ids})
                if attribute_line_ids_data:
                    attrib_line_vals.append(attribute_line_ids_data)
        return attrib_line_vals

    def open_variant_list(self):
        """
        This method used for smart button for view variant.
        @return: Action
        """
        form_view_id = self.env.ref('odoo_magento2_ept.view_magento_product_form').id
        tree_view = self.env.ref('odoo_magento2_ept.view_magento_product_tree').id
        action = {
            'name': 'Magento Product Variant',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.product.product',
            'views': [(tree_view, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [('id', 'in', self.magento_product_ids.ids)]
        }
        return action

    def open_export_product_in_magento_ept_wizard(self):
        view = self.env.ref('odoo_magento2_ept.magento_export_products_ept_wizard')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'magento.export.product.ept',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
        }

    def unlink_product_from_magento(self):
        m_product_ids = self.env.context.get('active_ids')
        if m_product_ids:
            self.browse(m_product_ids).write({'sync_product_with_magento': False,
                                          "magento_product_template_id": ''})
            if self.browse(m_product_ids).magento_product_ids:
                self.browse(m_product_ids).magento_product_ids.write({'sync_product_with_magento': False, "magento_product_id": ''})
        else:
            self.write({'sync_product_with_magento': False,"magento_product_template_id": ''})
            if self.magento_product_ids:
                self.magento_product_ids.write({'sync_product_with_magento': False, "magento_product_id": ''})
        return True

    @staticmethod
    def get_magento_product_images(simple_product_tmpl, product_type, is_it_child):
        if product_type == 'configurable' and not is_it_child:
            magento_product_images = simple_product_tmpl.magento_product_image_ids.filtered(
                lambda x: not x.exported_in_magento and not x.magento_product_id)
        elif product_type == 'simple' and is_it_child:
            magento_product_images = simple_product_tmpl.magento_product_image_ids.filtered(
                lambda x: not x.exported_in_magento and x.magento_product_id)
        else:
            magento_product_images = simple_product_tmpl.magento_product_image_ids.filtered(
                lambda x: not x.exported_in_magento)
        return magento_product_images

    def prepare_main_product_description_array(self, custom_attributes, product):
        sale_description_export = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_magento2_ept.set_magento_sales_description")
        if sale_description_export:
            if product.description:
                description = {"attribute_code": "description", "value": product.description}
                custom_attributes.append(description)
            if product.short_description:
                short_description = {"attribute_code": "short_description",
                                     "value": product.short_description}
                custom_attributes.append(short_description)
        return custom_attributes

    def find_category_website_for_the_product(self, product_type, is_it_child, product, instance):
        """
        Prepare the data for the website ID, Category ID
        :param product_type: Magento Product type
        :param is_it_child: True if product is child of configurable product
        :param product: product template object
        :param instance: Magento instance object
        :return: dictionary of categories
        """
        category = []
        if product_type == "simple" and is_it_child:
            category_ids = product.magento_tmpl_id.category_ids
            website_ids = self.get_magento_website_ids(instance, product.magento_tmpl_id)
        else:
            category_ids = product.category_ids
            website_ids = self.get_magento_website_ids(instance, product)
        for cat in category_ids:
            category.append({"position": 0, "category_id": cat.category_id})
        return {"website_id": website_ids, "category": category}

    @staticmethod
    def get_magento_website_ids(instance, product):
        if product.export_product_to_all_website:
            website_ids = instance.magento_website_ids
        else:
            website_ids = product.magento_website_ids
        return website_ids

    @staticmethod
    def get_magento_attribute_set(product, product_type, is_it_child, attribute_set_id,
                                  common_log_book_id):
        if product_type == 'simple' and is_it_child and not attribute_set_id:
            attribute_set = product.magento_tmpl_id.attribute_set_id.attribute_set_id
        elif not attribute_set_id:
            attribute_set = attribute_set_id.attribute_set_id if attribute_set_id \
                else product.attribute_set_id.attribute_set_id
        else:
            attribute_set = attribute_set_id.attribute_set_id
        if not attribute_set:
            common_log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': "Attribute set not set in the product template and wizard."
                               " \nNot able to create new Simple"
                               " Product in Magento. SKU : %s" % product.magento_sku,
                    'default_code': product.magento_sku
                })]
            })
        return attribute_set

    def get_magento_product_price(self, instance, conf_simple_product, magento_is_set_price,
                                  website, currency,
                                  common_log_book_id):
        product_price = 0

        if magento_is_set_price and instance.catalog_price_scope == 'global':
            product_price = self.get_scope_wise_product_price(
                instance, common_log_book_id, conf_simple_product, instance.pricelist_id)
        elif magento_is_set_price and instance.catalog_price_scope == 'website':
            price_list = website.pricelist_ids.filtered(lambda x: x.currency_id.id == currency)
            if price_list:
                price_list = price_list[0]
                product_price = self.get_scope_wise_product_price(instance, common_log_book_id,
                                                                  conf_simple_product,
                                                                  price_list)
        return product_price

    @staticmethod
    def get_scope_wise_product_price(instance, common_log_book_id, product, price_list, cost_price=False):
        """
        Get product price based on the price scope
        :param instance:  Magento Instance Object
        :param common_log_book_id: Common Log book object
        :param product: Product.product object
        :param price_list: Product Price list object
        :return:
        """
        product_price = 0
        _logger.info("Instance %s price scope is Global.", instance.name)
        if price_list:
            if price_list.item_ids.filtered(
                    lambda x: x.product_id.id == product.odoo_product_id.id or x.product_id.id == product.odoo_product_id.product_tmpl_id.id):
                product_price = price_list.get_product_price(product.odoo_product_id, price_list.id,
                                                             False)
                if not product_price:
                    if cost_price:
                        product_price = product.odoo_product_id.standard_price
                    else:
                        product_price = product.odoo_product_id.list_price
                _logger.info(
                    "Product : {} and product price is : {}".format(product.odoo_product_id.name,
                                                                    product_price))
            else:
                if cost_price:
                    product_price = product.odoo_product_id.standard_price
                else:
                    product_price = product.odoo_product_id.list_price
            # product_price = product.odoo_product_id.currency_id._convert(product_price, price_list.currency_id, self.env.company, datetime.now(), round=False)
        else:
            common_log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': "Still price list not set for the Instance : %s" % instance.name
                })]
            })
        return product_price

    @staticmethod
    def get_simple_product(is_it_child, product, product_type=False):
        if (not product_type or product_type and product_type == "simple") and is_it_child:
            conf_simple_product_product = product
        else:
            conf_simple_product_product = product.magento_product_ids[0] if \
                len(product.magento_product_ids) > 1 else product.magento_product_ids
        return conf_simple_product_product

    def prepare_export_images_values(self, simple_product_tmpl, product_type, is_it_child):
        """
        Prepare the product main and child image vals
        :param simple_product_tmpl: Simple product template
        :return:
        """
        media_gallery = []
        temp = 1
        main_product_img = False
        child_img = []
        if product_type == 'configurable' and not is_it_child:
            magento_product_images = simple_product_tmpl.magento_product_image_ids.filtered(
                lambda x: not x.magento_product_id)
        elif product_type == 'simple' and is_it_child:
            magento_product_images = simple_product_tmpl.magento_product_image_ids.filtered(
                lambda x: x.magento_product_id)
        else:
            magento_product_images = simple_product_tmpl.magento_product_image_ids
        if simple_product_tmpl.image_1920:
            main_product_img = simple_product_tmpl.image_1920
        for magento_product_image in magento_product_images:
            if main_product_img and magento_product_image.image == main_product_img and not magento_product_image.name:
                continue
            child_img.append(magento_product_image)
        if magento_product_images and not main_product_img and product_type == 'simple' and is_it_child:
            main_product_img = simple_product_tmpl.magento_tmpl_id.magento_product_image_ids.filtered(
                lambda x: x.sequence == 0 and not x.magento_product_id).image

        sku = simple_product_tmpl.magento_sku if simple_product_tmpl.magento_sku \
            else simple_product_tmpl.magento_product_name
        if main_product_img:
            self.prepare_export_image_values_dict(main_product_img, sku, temp, media_gallery, True)
        if child_img:
            for child_image in child_img:
                temp += 1
                self.prepare_export_image_values_dict(child_image.image, sku, temp, media_gallery,
                                                      False)
        return media_gallery

    def prepare_export_image_values_dict(self, image, sku, temp, media_gallery, is_main_img):
        cimg_format = self.find_export_image_format(image)
        cimg_base64 = image.decode()
        img_name = sku + "_%s.%s" % (temp, cimg_format)
        cimg_vals = self.prepare_image_vals_ept(cimg_base64, img_name, cimg_format, is_main_img)
        media_gallery.append(cimg_vals)

    @staticmethod
    def find_export_image_format(img):
        """
        Find th product image format
        :param img:  Image
        :return:
        """
        image_stream = io.BytesIO(codecs.decode(img, "base64"))
        image = Image.open(image_stream)
        img_format = image.format
        return img_format.lower()

    def prepare_image_vals_ept(self, img_base64, name, format, is_main_img=False):
        """
        Prepare the Product IMage vals
        :param img_base64: Image Base64 code
        :param name: Image name
        :param format: Image format
        :param is_main_img: Is the product main image?
        :return:
        """
        img_val = {
            "mediaType": "image",
            "label": name,
            "position": 0,
            "disabled": False,
            "types": ["image", "small_image", "thumbnail"] if is_main_img else [],
            "file": "",
            "content": {
                "Base64EncodedData": img_base64,
                "Type": "image/%s" % format,
                "Name": "%s" % name
            }
        }
        return img_val

    def search_website_vise_store_views(self, website, instance):
        """
        Find the store code for the store
        :param website: Magento website
        :param instance: Magento Instance
        :return:
        """
        return self.env['magento.storeview'].search([
            ('magento_website_id', '=', website.id), ('magento_instance_id', '=', instance.id)])

    @staticmethod
    def translate_description(
            export_product_data, store_view, custom_attributes,
            simple_product_tmpl, configurable_custom_attributes=[]):
        """
        convert the description and short description based on the store view lang
        :param export_product_data:
        :param store_view:
        :param custom_attributes:
        :param simple_product_tmpl:
        :return:
        """
        for attribute in custom_attributes:
            if attribute.get('attribute_code') == "description":
                product_description = simple_product_tmpl.with_context(
                    lang=store_view.lang_id.code).description
                export_product_data['product']['custom_attributes'].append(
                    {'attribute_code': 'description', 'value': product_description})
            if attribute.get('attribute_code') == "short_description":
                product_short_description = simple_product_tmpl.with_context(
                    lang=store_view.lang_id.code).short_description
                export_product_data['product']['custom_attributes'].append(
                    {'attribute_code': 'short_description',
                     'value': product_short_description})
        export_product_data['product']['name'] = simple_product_tmpl. \
            with_context(lang=store_view.lang_id.code).magento_product_name
        return export_product_data

    def set_website_in_product(
            self, instance, product, website_id, common_log_id,
            product_type, custom_attributes, is_it_child, magento_is_set_image):
        """
        Set website in magento product
        :param instance: Magento Instance
        :param product: Magento product object
        :param website_id: website ID
        :param common_log_id: log book record
        :param product_type: Magento product type
        :param custom_attributes: dictionary of custom attributes
        :param is_it_child: True if product is child product else False
        :param magento_is_set_image: True if export images else False
        :return:
        """
        try:
            conf_product_name = product.magento_product_name
            sku = product.magento_sku if product.magento_sku else product.magento_product_name
            api_url = '/all/V1/products/%s' % Php.quote_sku(sku)
            data = {
                "product": {
                    "sku": sku,
                    "name": conf_product_name,
                    "extension_attributes": {
                        "website_ids": website_id
                    },
                    "custom_attributes": custom_attributes
                }
            }
            if magento_is_set_image:
                media_gallery = self.prepare_export_images_values(product, product_type,
                                                                  is_it_child)
                if media_gallery:
                    data['product']['media_gallery_entries'] = media_gallery
            req(instance, api_url, 'PUT', data)
        except Exception:
            common_log_id.write({
                'log_lines': [(0, 0, {
                    'message': "Website can not able to assign in product SKU : %s in magento" % sku,
                    'default_code': sku
                })]
            })
        return True

    def write_product_id_in_odoo(self, response, product_type, is_it_child, product):
        """
        after response received set the product id in odoo and make that product is Sync with magento as true
        :param response: API response
        :param product_type: Product type
        :param is_it_child: Is this product child product of any configurable product
        :param product: product
        :return:
        """
        _logger.info("Product created in magento successfully with Product SKU : %s and "
                     "Product ID : %s" % (response.get('sku'), response.get('id')))
        if product_type == "simple" and not is_it_child:
            product.write({'sync_product_with_magento': True,
                           "magento_product_template_id": response.get('id')})
            _logger.info("Sync product with magento.product.template successfully")
            if len(product.magento_product_ids) == 1:
                product.magento_product_ids.write(
                    {"magento_product_id": response.get('id'), "sync_product_with_magento": True})
                _logger.info("Sync product with magento.product.product successfully")
        elif product_type == "configurable":
            product.write({
                'sync_product_with_magento': True,
                "magento_product_template_id": response.get('id'),
                "magento_sku": response.get('sku')})
        else:
            product.write(
                {"magento_product_id": response.get('id'), "sync_product_with_magento": True})
        self._cr.commit()
        return False

    def prepare_configurable_option_vals(self, conf_product_sku, common_log_book_id, instance,
                                         product,
                                         attribute_set_id):
        """
        Prepare the Vals for the configurable product options
        :param conf_product_sku: SKU for the configurable product
        :param common_log_book_id: Log book record
        :param instance: Magento Instance
        :return:
        """
        magento_att_obj = self.env['magento.product.attribute']
        attribute_line = product.attribute_line_ids
        skip = False
        for line in attribute_line:
            magento_att = magento_att_obj.search([
                ('odoo_attribute_id', '=', line.attribute_id.id),
                ('instance_id', '=', instance.id),
            ], limit=1)
            if not magento_att:
                magento_att = self.create_magento_attribute(line.attribute_id, instance)
            attribute_options = self.get_magento_attribute_options(magento_att, instance,
                                                                   line.value_ids)
            if magento_att and not magento_att.magento_attribute_id:
                skip = self.export_product_attribute_in_magento(
                    magento_att, instance, common_log_book_id, conf_product_sku, attribute_options)
                if skip:
                    return True
            elif magento_att and attribute_options:
                self.export_attribute_options(
                    magento_att, instance, common_log_book_id, conf_product_sku, attribute_options)
            is_attribute_assigned = self.check_attribute_in_magento(
                instance, attribute_set_id, magento_att.magento_attribute_id)
            if not is_attribute_assigned and attribute_set_id:
                skip = self.assign_attribute_in_attribute_set(
                    instance, product, attribute_set_id, common_log_book_id,
                    magento_att.magento_attribute_id)
                if skip:
                    return True
            if magento_att:
                self.export_attribute_in_magento(magento_att, line, conf_product_sku, instance,
                                                 common_log_book_id)
            else:
                # this else for attribute is not for the Magento
                common_log_book_id.write({
                    'log_lines': [(0, 0, {
                        'message': "Can't find attribute option in "
                                   "Magento Attribute Option list : %s" % line.attribute_id.name
                    })]
                })
                return True
        return skip

    def export_attribute_in_magento(self, magento_att, line, conf_product_sku, instance,
                                    common_log_book_id):
        '''
        Export product attribute in magneto
        :param magento_att: magento attributes
        :param line:  attibute value ids
        :param conf_product_sku: create attribute for products
        :param instance: magento instance
        :param common_log_book_id: log book ids
        :return: true
        '''
        opt_val = {
            "option": {
                "attribute_id": magento_att.magento_attribute_id,
                "label": magento_att.name,
                "position": 0,
                "is_use_default": True,
                "values": [
                    {
                        "value_index": line.id
                    }
                ]
            }
        }
        try:
            api_url = '/V1/configurable-products/%s/options' % Php.quote_sku(
                conf_product_sku)
            req(instance, api_url, 'POST', opt_val)
        except Exception:
            common_log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': "Attribute options can not able to assign in product SKU : %s in magento" % conf_product_sku,
                    'default_code': conf_product_sku
                })]
            })
            return True

    def create_magento_attribute(self, attribute_id, instance_id):
        attribute_options = self.prepare_attribute_options_dict(attribute_id, instance_id)
        attribute_name = attribute_id.name.replace(" ", "_")
        attribute_values = {
            'name': attribute_id.name,
            'odoo_attribute_id': attribute_id.id,
            'instance_id': instance_id.id,
            'magento_attribute_code': attribute_name,
            'frontend_label': attribute_id.name,
            'attribute_type': 'select',
            'option_ids': attribute_options
        }
        return self.env['magento.product.attribute'].create(attribute_values)

    @staticmethod
    def prepare_attribute_options_dict(attribute_id, instance_id):
        attribute_options_dict = []
        for attribute_option in attribute_id.value_ids:
            attribute_options_dict.append((0, 0, {
                'name': attribute_option.name,
                'magento_attribute_option_name': attribute_option.name,
                'odoo_attribute_id': attribute_id.id,
                'instance_id': instance_id.id,
                'odoo_option_id': attribute_option.id
            }))
        return attribute_options_dict

    def export_product_attribute_in_magento(
            self, magento_attribute, instance, common_log_book_id, sku, attribute_options):
        option = self.env['magento.attribute.option']
        attribute_code = magento_attribute.magento_attribute_code.replace(" ", "_")
        attribute_data = {
            "attribute": {
                "attribute_code": attribute_code.lower(),
                "frontend_input": "select",
                "options": attribute_options,
                "default_frontend_label": magento_attribute.name,
                "is_unique": "0"
            }
        }
        response = ''
        try:
            api_url = '/V1/products/attributes/'
            response = req(instance, api_url, 'POST', attribute_data)
        except Exception:
            common_log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': "In Magento can not able to  create new attribute for product SKU : %s" % sku,
                    'default_code': sku
                })]
            })
            # it means we not need to process further steps
            return True
        if response:
            option.write({'magento_attribute_id': response.get('attribute_id')})
            for attribute_value in response.get('options'):
                option = option.search([
                    ('name', '=', attribute_value.get('label', '-')),
                    ('odoo_attribute_id', '=', magento_attribute.odoo_attribute_id.id),
                    ('magento_attribute_id', '=', magento_attribute.id)])
                if attribute_value.get('value', ''):
                    option.write({'magento_attribute_option_id': attribute_value.get('value')})
        # it means we need to process further steps
        return False

    @staticmethod
    def check_attribute_in_magento(instance, attribute_set_id,
                                   magento_attribute_id):
        '''
        Check attribute is exist in attribute set in magento.
        :param instance: magento instance
        :param attribute_set_id: magento attribute set id
        :param magento_attribute_id: magento attribute
        :return:
        '''
        try:
            api_url = '/V1/products/attribute-sets/%s/attributes' % attribute_set_id.attribute_set_id
            magento_attributes = req(instance, api_url, 'GET')
            for magento_attribute in magento_attributes:
                if magento_attribute.get('attribute_id') == int(magento_attribute_id):
                    return True
        except Exception:
            pass
        return False

    def assign_attribute_in_attribute_set(self, instance, product, attribute_set_id,
                                          common_log_book_id,
                                          attribute_code):
        attribute_set_id = self.get_magento_attribute_set(
            product, 'configurable', False, attribute_set_id, common_log_book_id)
        attribute_set = self.env['magento.attribute.set'].search([
            ('attribute_set_id', '=', attribute_set_id), ('instance_id', '=', instance.id)])
        attribute_data = {
            "attributeSetId": attribute_set_id,
            "attributeGroupId": 1,
            "attributeCode": attribute_code,
            "sort_order": 10
        }
        try:
            api_url = '/V1/products/attribute-sets/attributes'
            req(instance, api_url, 'POST', attribute_data)
        except Exception:
            common_log_book_id.write({
                'log_lines': [(0, 0, {
                    'message': "Product attribute %s is not assign in attribute set : %s in magento" % (
                        attribute_code, attribute_set.attribute_set_name),
                    'default_code': product.magento_sku
                })]
            })
            return True
        return False

    def get_magento_attribute_options(self, magento_attribute, instance, odoo_attribute_options):
        attribute_options = []
        for attribute_option in odoo_attribute_options:
            magento_attr_opt = self.env['magento.attribute.option'].search([
                ('magento_attribute_id', '=', magento_attribute.id),
                ('instance_id', '=', instance.id),
                ('odoo_option_id', '=', attribute_option.id)])
            if not magento_attr_opt or (
                    magento_attr_opt and not magento_attr_opt.magento_attribute_option_id):
                attribute_options.append({"label": attribute_option.name})
        return attribute_options

    def export_attribute_options(self, magento_attribute, instance,
                                 common_log_book_id, sku,
                                 attribute_options):
        '''
        Export Product Attribute options in magento and set it in proper attribute set.
        :param magento_attribute: magento attribute set
        :param instance:  magento instance
        :param common_log_book_id: logbook id
        :param sku: product sku for add log
        :param attribute_options: attribute options
        :return:
        '''
        for attribute_option in attribute_options:
            attribute_options_data = {"option": attribute_option}
            try:
                api_url = '/V1/products/attributes/%s/options' % magento_attribute.magento_attribute_id
                response = req(instance, api_url, 'POST', attribute_options_data)
                if response:
                    self.env['magento.product.attribute'].create_product_attribute_in_odoo(
                        instance, magento_attribute.magento_attribute_id, magento_attribute)
            except Exception:
                common_log_book_id.write({
                    'log_lines': [(0, 0, {
                        'message': "Not able to create attribute for product SKU : %s" % sku,
                        'default_code': sku
                    })]
                })
        return True

    @staticmethod
    def bind_simple_with_configurable_product(
            instance, product_magento_sku_list, conf_product_sku, common_log_id):
        """
        Bind the simple product to their configurable product
        :param instance: instance record
        :param product_magento_sku_list: Simple product SKU
        :param conf_product_sku: Configurable product SKU
        :param common_log_id: log book record ID
        :return:
        """
        for product_magento_sku in product_magento_sku_list:
            try:
                data = {
                    "childSku": product_magento_sku
                }
                api_url = f'/V1/configurable-products/{Php.quote_sku(conf_product_sku)}/child'
                req(instance, api_url, 'POST', data)
            except Exception:
                message = f"""
                Not able to Bind simple product : {product_magento_sku} with Configurable Product : 
                {conf_product_sku} in Magento.
                -Possibly, Magento configurable product attributes are not of type dropdown. 
                """
                common_log_id.write({
                    'log_lines': [(0, 0, {
                        'message': message,
                        'default_code': product_magento_sku
                    })]
                })
        return True

    @staticmethod
    def update_product_request(instance, data, api_url):
        """
        Update product request
        :param instance: Magento Instance
        :param data: body data
        :param api_url: API URL
        :param sku: Magento product SKU
        :param common_log_id: log book record
        :return:
        """
        req(instance, api_url, 'PUT', data, is_raise=True)
        return True

    @staticmethod
    def update_product_base_price(instance, url, common_log_id, price_payload):
        """
        Update product basic price in magento
        :param instance: Magento Instance
        :param url: API URL
        :param common_log_id: Common log book record
        :param price_payload: price body
        :return:
        """
        try:
            req(instance, url, 'POST', price_payload, is_raise=True)
        except Exception as error:
            common_log_id.write({
                'log_lines': [(0, 0, {
                    'message': f"Not able to update product price. Error : {error}",
                })]
            })
        return True

    def prepare_export_stock_data(self, product_stock, instance, log, layer_ids, source_code=False,
                                  msi=False):
        """
        Export stock in magento
        :param product_stock: Stock item
        :param instance: Magento Instance
        :param log: Common log record
        :param source_code: if MSI then location source code
        :param msi: IS the MSI
        :return:
        """
        consumable, stock_data = [], []
        m_product = self.env['magento.product.product']
        for product_id, stock in product_stock.items():
            product = [product for product in layer_ids if
                       product.get('id') == product_id and product.get('magento_sku')][0]
            if product and stock >= 0.0:
                if product.get('type') != 'product':
                    consumable.append(product.odoo_product_id.default_code)
                else:
                    if msi:
                        stock_data.append({
                            'sku': product.get('magento_sku'),
                            'source_code': source_code,
                            'quantity': stock,
                            'status': 1
                        })
                    else:
                        stock_data.append({
                            'sku': product.get('magento_sku'),
                            'qty': stock,
                            'is_in_stock': 1
                        })
            if consumable:
                m_product.create_export_product_process_log(consumable, log)
        return stock_data

    def open_product_in_magento(self):
        """
        This method is used for open product in magento
        """
        m_url = self.magento_instance_id.magento_admin_url
        m_product_id = self.magento_product_template_id
        if m_url:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s/catalog/product/edit/id/%s' % (m_url, m_product_id),
                'target': 'new',
            }
