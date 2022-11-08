# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields and methods for Magento products
"""
import logging
import math
import json
from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError
from .api_request import req, create_search_criteria
from ..python_library.php import Php

_logger = logging.getLogger('MagentoEPT')


class MagentoProductProduct(models.Model):
    """
    Describes fields and methods for Magento products
    """
    _name = 'magento.product.product'
    _description = 'Magento Product'
    _rec_name = 'magento_product_name'

    magento_instance_id = fields.Many2one(comodel_name='magento.instance',
                                          string='Instance',
                                          help="This field relocates magento instance")
    magento_product_id = fields.Char(string="Magento Product", help="Magento Product Id")
    magento_product_name = fields.Char(string="Magento Product Name",
                                       help="Magento Product Name", translate=True)
    magento_tmpl_id = fields.Many2one(comodel_name='magento.product.template',
                                      string="Magento Product template",
                                      help="Magento Product template", ondelete="cascade")
    odoo_product_id = fields.Many2one(comodel_name='product.product', string='Odoo Product',
                                      required=True, ondelete='restrict', copy=False)
    magento_website_ids = fields.Many2many(comodel_name='magento.website',
                                           string='Magento Websites', readonly=False,
                                           domain="[('magento_instance_id','=',magento_instance_id)]",
                                           help='Magento Websites')
    product_type = fields.Selection([('simple', 'Simple Product'),
                                     ('configurable', 'Configurable Product'),
                                     ('virtual', 'Virtual Product'),
                                     ('downloadable', 'Downloadable Product'),
                                     ('group', 'Group Product'),
                                     ('bundle', 'Bundle Product'),
                                     ], string='Magento Product Type', help='Magento Product Type',
                                    default='simple')
    created_at = fields.Date(string='Product Created At',
                             help="Date when product created into Magento")
    updated_at = fields.Date(string='Product Updated At',
                             help="Date when product updated into Magento")

    magento_sku = fields.Char(string="Magento Product SKU", help="Magento Product SKU")
    description = fields.Text(string="Product Description", help="Description", translate=True)
    short_description = fields.Text(string='Product Short Description',
                                    help='Short Description', translate=True)
    magento_product_image_ids = fields.One2many('magento.product.image', 'magento_product_id',
                                                string="Magento Product Images",
                                                help="Magento Product Images")
    sync_product_with_magento = fields.Boolean(string='Sync Product with Magento',
                                               help="If Checked means, Product "
                                                    "synced With Magento Product")
    active_product = fields.Boolean(string='Odoo Product Active', related="odoo_product_id.active")
    active = fields.Boolean(string="Active", default=True)
    image_1920 = fields.Image(related="odoo_product_id.image_1920")
    product_template_attribute_value_ids = fields.Many2many(
        related='odoo_product_id.product_template_attribute_value_ids')
    qty_available = fields.Float(related='odoo_product_id.qty_available')
    lst_price = fields.Float(related='odoo_product_id.lst_price')
    standard_price = fields.Float(related='odoo_product_id.standard_price')
    currency_id = fields.Many2one(related='odoo_product_id.currency_id')
    valuation = fields.Selection(related='odoo_product_id.product_tmpl_id.valuation')
    cost_method = fields.Selection(related='odoo_product_id.product_tmpl_id.cost_method')
    company_id = fields.Many2one(related='odoo_product_id.company_id')
    uom_id = fields.Many2one(related='odoo_product_id.uom_id')
    uom_po_id = fields.Many2one(related='odoo_product_id.uom_po_id')
    total_magento_variants = fields.Integer(related='magento_tmpl_id.total_magento_variants')

    _sql_constraints = [('_magento_product_unique_constraint',
                         'unique(magento_sku,magento_instance_id,magento_product_id,magento_tmpl_id)',
                         "Magento Product must be unique")]

    def unlink(self):
        unlink_magento_products = self.env['magento.product.product']
        unlink_magento_templates = self.env['magento.product.template']
        for magento_product in self:
            # Check if the product is last product of this template...
            if not unlink_magento_templates or (
                    unlink_magento_templates and unlink_magento_templates != magento_product.magento_tmpl_id):
                unlink_magento_templates |= magento_product.magento_tmpl_id
            unlink_magento_products |= magento_product
        res = super(MagentoProductProduct, unlink_magento_products).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        if not unlink_magento_templates.magento_product_ids:
            unlink_magento_templates.unlink()
        self.clear_caches()
        return res

    def toggle_active(self):
        """ Archiving related magento.product.template if there is not any more active magento.product.product
        (and vice versa, unarchiving the related magento product template if there is now an active magento.product.product) """
        result = super().toggle_active()
        # We deactivate product templates which are active with no active variants.
        tmpl_to_deactivate = self.filtered(lambda product: (product.magento_tmpl_id.active
                                                            and not product.magento_tmpl_id.magento_product_ids)).mapped(
            'magento_tmpl_id')
        # We activate product templates which are inactive with active variants.
        tmpl_to_activate = self.filtered(lambda product: (not product.magento_tmpl_id.active
                                                          and product.magento_tmpl_id.magento_product_ids)).mapped(
            'magento_tmpl_id')
        (tmpl_to_deactivate + tmpl_to_activate).toggle_active()
        return result

    def view_odoo_product(self):
        """
        This method id used to view odoo product.
        :return: Action
        """
        if self.odoo_product_id:
            vals = {
                'name': 'Odoo Product',
                'type': 'ir.actions.act_window',
                'res_model': 'product.product',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', '=', self.odoo_product_id.id)],
            }
            return vals

    @staticmethod
    def update_custom_option(item):
        extension = item.get('extension_attributes', {})
        if isinstance(item.get('custom_attributes', []), list):
            attributes = {}
            for attribute in item.get('custom_attributes', []):
                attributes.update({attribute.get('attribute_code'): attribute.get('value')})
            attributes and item.update({'custom_attributes': attributes})
        if isinstance(extension.get('website_wise_product_price_data', []), list):
            prices = []
            for price in extension.get('website_wise_product_price_data', []):
                if isinstance(price, str):
                    prices.append(json.loads(price))
            prices and extension.update({'website_wise_product_price_data': prices})
        return True

    def search_product_in_layer(self, line, item):
        self.update_custom_option(item)
        m_product = self.search(
            ['|', ('magento_product_id', '=', item.get('id')), ('magento_sku', '=', item.get('sku')),
             ('magento_instance_id', '=', line.instance_id.id)], limit=1)
        if not m_product:
            m_product = self.search(['|', ('magento_product_id', '=', item.get('id')),
                                     ('magento_sku', '=', item.get('sku')),
                                     ('magento_instance_id', '=', line.instance_id.id),
                                     ('active', '=', False)], limit=1)
            m_product.write({'active': True})
        if m_product:
            m_template = m_product.magento_tmpl_id
            product = m_product.odoo_product_id
            if 'is_order' not in list(self.env.context.keys()):
                if not line.do_not_update_existing_product:
                    self.__update_layer_product(line, item, m_product)
                    m_template.update_layer_template(line, item, product)
        else:
            product = self._search_odoo_product(line, item)
        prices = item.get('extension_attributes', {}).get('website_wise_product_price_data', [])
        if 'is_order' not in list(self.env.context.keys()):
            if not line.do_not_update_existing_product and prices and product:
                self.__update_prices(prices)
                self.env['magento.product.template'].update_price_list(line, product, prices)
        return product

    @staticmethod
    def __update_prices(prices):
        for price in prices:
            price.update({
                'price': price.get('product_price'),
                'currency': price.get('default_store_currency'),
            })

    def __update_layer_product(self, line, item, m_product):
        product = m_product.odoo_product_id
        instance = line.instance_id
        m_template = m_product.magento_tmpl_id
        data = self.magento_tmpl_id.get_website_category_attribute_tax_class(item, instance)
        values = self._prepare_layer_product_values(m_template, product, item, data)
        values.pop('magento_product_id')
        m_product.write(values)
        if instance.allow_import_image_of_products:
            m_template = self.env['magento.product.template']
            # We will only update/create image in layer and odoo product if customer has
            # enabled the configuration from instance.
            images = m_template.get_product_images(item, data, line)
            m_template.create_layer_image(instance, images, variant=m_product)
        return True

    def _search_odoo_product(self, line, item):
        product = self.env['product.product']
        product = product.search([('default_code', '=', item.get('sku'))], limit=1)
        if not product:
            if line.instance_id.auto_create_product:
                product = self._create_odoo_product(item)
            else:
                # create log and inform that customer has not enabled the
                # auto_create_product in the instance.
                is_verify = self.verify_configuration(line, item)
                return is_verify
        # If product is found then we will create mapping of that odoo product in Magento
        # layer and Magento product
        self._map_product_in_layer(line, item, product)
        return product

    def _create_odoo_product(self, item):
        self.update_custom_option(item)
        values = self._prepare_product_values(item)
        return self.env['product.product'].create(values)

    def _create_odoo_template(self, item):
        self.update_custom_option(item)
        values = self._prepare_product_values(item)
        return self.env['product.template'].create(values)

    def _prepare_product_values(self, item):
        values = {
            'name': item.get('name'),
            'default_code': item.get('sku'),
            'type': 'product',
            'invoice_policy': 'order'
        }
        description = self.prepare_description(item)
        if description:
            values.update(description)
        return values

    def prepare_description(self, item, is_layer=False):
        description = {}
        ipc = self.env['ir.config_parameter'].sudo()
        ipc = ipc.get_param('odoo_magento2_ept.set_magento_sales_description')
        if ipc:
            attribute = item.get('custom_attributes', {})
            if is_layer:
                description.update({
                    'description': attribute.get('description'),
                    'short_description': attribute.get('short_description')
                })
            else:
                description.update({
                    'description': attribute.get('description'),
                    'description_sale': attribute.get('short_description')
                })
        return description

    def _map_product_in_layer(self, line, item, product):
        template = self.env['magento.product.template']
        template = template.create_template(line, item, product)
        self._create_product(template, product, item, line)
        return True

    def _create_product(self, template, product, item, line):
        instance = line.instance_id
        data = self.magento_tmpl_id.get_website_category_attribute_tax_class(item, instance)
        values = self._prepare_layer_product_values(template, product, item, data)
        m_product = self.search([('magento_product_id', '=', item.get('id'))], limit=1)
        if not m_product:
            m_product = self.create(values)
        if instance.allow_import_image_of_products:
            m_template = self.env['magento.product.template']
            # We will only update/create image in layer and odoo product if customer has
            # enabled the configuration from instance.
            images = m_template.get_product_images(item, data, line)
            m_template.create_layer_image(instance, images, variant=m_product)
        return m_product

    def _prepare_layer_product_values(self, template, product, item, data):
        values = {
            'odoo_product_id': product.id,
            'magento_instance_id': template.magento_instance_id.id,
            'magento_product_id': item.get('id'),
            'magento_sku': item.get('sku'),
            'magento_product_name': item.get('name'),
            'magento_tmpl_id': template.id,
            'created_at': datetime.strptime(item.get('created_at'), '%Y-%m-%d %H:%M:%S').date(),
            'updated_at': datetime.strptime(item.get('created_at'), '%Y-%m-%d %H:%M:%S').date(),
            'product_type': item.get('type_id'),
            'magento_website_ids': [(6, 0, data.get('website'))],
            'sync_product_with_magento': True
        }
        description = self.prepare_description(item, is_layer=True)
        if description:
            values.update(description)
        return values

    def import_configurable_product(self, line, item):
        template = self.env['product.template']
        m_template = self.env['magento.product.template']
        link = item.get('extension_attributes').get('configurable_product_link_data')
        magento_sku = ''
        if link:
            link = json.loads(link[0])
            magento_sku = link.get('simple_product_sku')
        self.__update_child_response(item)
        m_template = m_template.search([('magento_product_template_id', '=', item.get('id')),
                                        ('magento_instance_id', '=', line.instance_id.id)], limit=1)
        if not m_template:
            m_template = m_template.search([('magento_product_template_id', '=', item.get('id')),
                                            ('magento_instance_id', '=', line.instance_id.id), ('active', '=', False)], limit=1)
            m_template.write({'active': True})

        if not m_template:
            m_template = self.search([('magento_sku', '=', magento_sku), (
                'magento_instance_id', '=', line.instance_id.id)]).magento_tmpl_id
            
        if not template:
            template = self.search_odoo_product_template_exists(magento_sku, item)
            if not template:
                is_verify = self.verify_configuration(line, item)
                if is_verify:
                    template = self._create_odoo_template(item)
                else:
                    return is_verify
        if line.instance_id.auto_create_product:
            return m_template.create_configurable_template(line, item, template)
        elif not template:
            return self.search_odoo_product_template_exists(magento_sku, item)
        else:
            # Create log for do not update product
            return self.verify_configuration(line, item)
    
    def search_odoo_product_template_exists(self, magento_sku, item):
        """
        Search Odoo product template exists or not.
        :param magento_sku: SKU received from Magento
        :param item: item received from Magento
        :return: odoo product template object or False
        """
        product_obj = self.env['product.product']
        magento_product_obj = self.env['magento.product.product']
        magento_product_product = magento_product_obj.search([('magento_sku', '=', magento_sku)])
        if magento_product_product:
            existing_products = magento_product_product.odoo_product_id
        else:
            existing_products = product_obj.search([('default_code', '=', magento_sku)])
        if not existing_products:
            # not getting product.product record using SKU then search in magento.product.product.
            # product not exist in odoo variant but exist in magento variant layer
            magento_product_template = self.search([('magento_sku', '=', item.get('sku'))], limit=1)
            odoo_template_id = magento_product_template.magento_tmpl_id.odoo_product_template_id if \
                magento_product_template else False
        else:
            odoo_template_id = existing_products and existing_products[0].product_tmpl_id
        return odoo_template_id

    def verify_configuration(self, line, item):
        log = line.queue_id.log_book_id
        instance = line.instance_id
        if not instance.auto_create_product:
            message = f"Odoo Product Not found for SKU : {item.get('sku')}, \n" \
                      f"And 'Auto Create Product' configuration is off. \n" \
                      f"Go to Settings -> Select Instance -> Enable the 'Auto Create Product'." \
                      f"configuration."
            key = 'import_product_queue_line_id'
            if 'is_order' in (self.env.context.keys()):
                key = 'magento_order_data_queue_line_id'
            log.write({'log_lines': [(0, 0, {
                'message': message,
                'order_ref': item.get('increment_id', ''),
                'default_code': item.get('sku'),
                key: line.id
            })]})
            line.queue_id.write({'is_process_queue': False})
            self._cr.commit()
            return False
        return True

    @staticmethod
    def __update_child_response(item):
        attributes = item.get('extension_attributes')
        keys = {
            'child_products': 'configurable_product_link_data',
            'attributes': 'configurable_product_options_data'
        }
        for key, value in keys.items():
            data = []
            if value in list(attributes.keys()):
                for child in attributes.get(keys.get(key), []):
                    data.append(json.loads(child))
            item.get('extension_attributes', {}).update({key: data})
            item.get('extension_attributes', {}).pop(value)
        return True

    def get_products(self, instance, ids, line):
        args = ''
        for id in ids:
            args += f"{id},"
        url = f"/V1/products?searchCriteria[filterGroups][0][filters][0][field]=entity_id" \
              f"&searchCriteria[filterGroups][0][filters][0][condition_type]=in" \
              f"&searchCriteria[filterGroups][0][filters][0][value]={args}"
        response = {}
        try:
            _logger.info("Sending request to get Configurable product of Child....")
            response = req(instance, url, is_raise=True)
        except Exception as error:
            _logger.error(error)
        if response:
            response = response.get('items', [])
            return self.__verify_product_response(response, ids, line)
        return response

    def __verify_product_response(self, response, ids, line):
        log = line.queue_id.log_book_id
        response_ids = [item.get('id') for item in response]
        key = 'default_code'
        field = 'import_product_queue_line_id'
        if 'is_order' in list(self.env.context.keys()):
            key = 'order_ref'
            field = 'magento_order_data_queue_line_id'
        for id in ids:
            if isinstance(id, str):
                id = int(id)
            if id not in response_ids:
                message = f"Magento Product Not found for ID {id}"
                log.write({'log_lines': [(0, 0, {
                    'message': message,
                    key: line.magento_id if key == 'order_ref' else line.product_sku,
                    field: line.id
                })]})
                return []
        return response

    def search_service_product(self, item, line):
        log = line.queue_id.log_book_id
        is_order = bool('is_order' in list(self.env.context.keys()))
        o_product = self.env['product.product']
        m_product = self.env['magento.product.product']
        m_product = m_product.search([('magento_product_id', '=', item.get('id'))], limit=1)
        if m_product:
            o_product = m_product.odoo_product_id
        if not o_product:
            o_product = o_product.search([('default_code', '=', item.get('sku'))], limit=1)
        if o_product:
            self.update_custom_option(item)
            self._map_product_in_layer(line, item, o_product)
        elif is_order:
            message = _(f"""
                        -Order {item.get('increment_id')} was skipped because when importing 
                        order the product {item.get('sku')} could not find in the odoo.
                        -Please create the product in Odoo with the same SKU to import the order.  
                        """)
            log.write({'log_lines': [(0, 0, {
                'message': message,
                'order_ref': item.get('increment_id', ''),
                'magento_order_data_queue_line_id': line.id
            })]})
            return False
        elif not is_order:
            message = _(f"Product SKU: {item.get('sku')} and Product Type: {item.get('type_id')}"
                        f"is not found in the odoo.\n"
                        f"Please create the product in Odoo with the same SKU to map the product "
                        f"in layer.")
            log.write({'log_lines': [(0, 0, {
                'message': message,
                'default_code': item.get('sku', ''),
                'import_product_queue_line_id': line.id
            })]})
            return False
        return True

    def update_magento_product(self, item, magento_websites, instance, magento_product):
        """
        magento product found, then prepare the new magento product vals and write it
        :param item: product item API response
        :param magento_websites: website data
        :param instance:  magento instance
        :param magento_product: magento product object
        :return:
        """
        values = self.prepare_magento_product_vals(item, magento_websites, instance.id)
        values.update({
            'magento_product_id': item.get('id'),
            'magento_tmpl_id': magento_product.magento_tmpl_id.id,
            'odoo_product_id': magento_product.odoo_product_id.id,
            'sync_product_with_magento': True
        })
        # Below code is for all the configurable's simple product is only simple product in odoo
        # not map all this odoo simple with configurable's simple product
        # and import configurable product, so set all the simple product's id and sync as true
        # in magento.product.template
        magento_product_tmpl = self.env['magento.product.template'].search(
            [('magento_product_template_id', '=', False), ('sync_product_with_magento', '=', False),
             ('magento_sku', '=', magento_product.magento_sku)])
        if magento_product_tmpl:
            magento_product_tmpl.write({
                'magento_product_template_id': item.get('id'),
                'sync_product_with_magento': True
            })
        magento_product.write(values)

    def map_odoo_product_with_magento_product(
            self, instance, magento_product, item, log_book_id, order_ref, queue_line,
            order_data_queue_line_id, error
    ):
        """
        Map Odoo Product with existing Magneto Product in Layer
        :param instance: Magento Instance Object
        :param magento_product: Magento product product object
        :param item: Response received from Magento
        :param log_book_id: Common log book object
        :param order_ref: Order reference
        :param queue_line: product or order queue line
        :param order_data_queue_line_id: data queue line object
        :param error: True if error else False
        :return: Log book id, error
        """
        magento_sku = item.get('sku')
        odo_product = magento_product.odoo_product_id.filtered(
            lambda x: x.default_code == magento_sku)
        if not odo_product:
            odoo_product, error = self.create_odoo_product(
                magento_sku, item, instance, log_book_id,
                order_ref, queue_line, order_data_queue_line_id, error
            )
            if odoo_product:
                magento_product.write({'odoo_product_id': [(0, 0, [odoo_product])]})
        return error

    def import_product_inventory(self, instance, auto_apply):
        """
        This method is used to import product stock from magento,
        when Multi inventory sources is not available.
        It will create a product inventory.
        :param instance: Instance of Magento
        :param validate_stock: Stock Validation confirmation
        :return: True
        """
        quant = self.env['stock.quant']
        log = self.env['common.log.book.ept']
        warehouse = instance.import_stock_warehouse
        location = warehouse and warehouse.lot_stock_id
        if location:
            api_url = '/V1/stockItems/lowStock?scopeId=0&qty=10000000000&pageSize=100000'
            response = req(instance, api_url)
            stock_data = self.prepare_import_stock_dict(response, instance)
            product_qty = stock_data.get('product_qty')
            consumable = stock_data.get('consumable')
            if product_qty:
                name = f'Inventory For Instance "{instance.name}" And Magento Location ' \
                       f'"{warehouse.name}"'
                quant.create_inventory_adjustment_ept(product_qty, location, auto_apply, name)
            if consumable:
                model_id = self.env['common.log.lines.ept'].get_model_id('stock.quant')
                log = log.create_common_log_book('import', 'magento_instance_id',
                                                 instance, model_id, 'magento_ept')
                self.create_consumable_products_log(consumable, log)
        else:
            raise UserError(_(f"Please Choose Import product stock for {warehouse.name} location"))
        return log

    def import_product_multi_inventory(self, instance, m_locations, auto_apply):
        """
        This method is used to import product stock from magento,
        when Multi inventory sources is available.
        It will create a product inventory.
        :param instance: Instance of Magento
        :param auto_apply: Stock Validation confirmation
        :param m_locations: Magento products object
        :return: True
        """
        quant = self.env['stock.quant']
        log = self.env['common.log.book.ept']
        if instance.is_import_product_stock:
            consumable = []
            for m_location in m_locations:
                warehouse = m_location.import_stock_warehouse
                location = warehouse and warehouse.lot_stock_id
                if location:
                    search_criteria = create_search_criteria(
                        {'source_code': m_location.magento_location_code})
                    query_string = Php.http_build_query(search_criteria)
                    api_url = f'/V1/inventory/source-items?{query_string}'
                    response = req(instance, api_url)
                    stock_data = self.prepare_import_stock_dict(response, instance)
                    name = f'Inventory For Instance "{instance.name}" And Magento Location ' \
                           f'"{warehouse.name}"'
                    quant.create_inventory_adjustment_ept(stock_data.get('product_qty'), location,
                                                          auto_apply, name)
                    consumable += stock_data.get('consumable')
                else:
                    raise UserError(
                        _("Please Choose Import product stock location for {m_location.name}"))
            if consumable:
                model_id = self.env['common.log.lines.ept'].get_model_id('stock.quant')
                log = log.create_common_log_book('import', 'magento_instance_id', instance,
                                                 model_id, 'magento_ept')
                self.create_consumable_products_log(consumable, log)
        return log

    def prepare_import_stock_dict(self, response, instance):
        """
        Prepare dictionary for import product stock from response.
        :param response: response received from Magento
        :param instance: Magento Instance object
        :param consumable: Dictionary of consumable products
        :param product_qty: Dictionary for import product stock
        :return: stock_to_import, consumable_products
        """
        consumable, product_qty = [], {}
        items = response.get('items', [])
        for item in items:
            m_product = self.search_magento_product(instance, item)
            if m_product:
                if instance.is_multi_warehouse_in_magento:
                    qty = item.get('quantity', 0) or 0
                else:
                    qty = item.get('qty', 0) or 0
                if qty > 0 and m_product.odoo_product_id.type == 'product':
                    product_qty.update({m_product.odoo_product_id.id: qty})
                elif m_product.odoo_product_id.type != 'product':
                    consumable.append(m_product.odoo_product_id.default_code)
        return {
            'consumable': consumable,
            'product_qty': product_qty
        }

    def search_magento_product(self, instance, item):
        """Create product search domain and search magento product
        :param: instance : instance object
        :param: item : item dict
        return product search domain"""
        domain = [('magento_instance_id', '=', instance.id),
                  ('magento_website_ids', '!=', False)]
        if instance.is_multi_warehouse_in_magento:
            domain.append(('magento_sku', '=', item.get('sku', '') or ''))
        else:
            domain.append(('magento_product_id', '=', item.get('product_id', 0) or 0))
        return self.search(domain, limit=1)

    @staticmethod
    def create_consumable_products_log(consumable_products, log):
        """
        Generate process log for import product stock with consumable product.
        :param consumable_products: dictionary of consumable products
        :param log: common log book object
        """
        if consumable_products:
            message = f"""
            The following products have not been imported due to
            product type is other than 'Storable.'\n {str(list(set(consumable_products)))} 
            """
            log.write({
                'log_lines': [(0, 0, {
                    'message': message
                })]
            })

    @staticmethod
    def create_export_product_process_log(consumable, log):
        """
        Generate process log for export product stock with consumable product.
        :param consumable: dictionary of consumable products
        :param log: common log book object
        """
        if consumable:
            message = f"""
            The following products have not been exported due to
            product type is other than 'Storable.'\n {str(list(set(consumable)))} 
            """
            log.write({
                'log_lines': [(0, 0, {
                    'message': message
                })]
            })

    def exp_prd_stock_in_batches(self, stock_data, instance, api_url, data_key, method, job):
        """
        Export product stock in a bunch of 100 items.
        :param stock_data: dictionary for stock data
        :param instance: magento instance object
        :param api_url: export stock API url
        :param data_key: API dictionary key
        :param method: API method
        :param job: common log book object
        :return: common log book object
        """
        stock_queue_obj = self.env['magento.export.stock.queue.ept']
        batch_size = 0
        for batch in range(0, len(stock_data) + 1, instance.batch_size):
            batch_size += instance.batch_size
            data = {data_key: stock_data[batch: batch_size]}
            if data:
                stock_queue_obj.create_export_stock_queues(instance, data)
        return True

    @staticmethod
    def call_export_product_stock_api(instance, api_url, data, log, method, line):
        """
        Call export product stock API for single or multi tracking inventory.
        :param instance: Magento instance object
        :param api_url: API Call URL
        :param data: Dictionary to be passed.
        :param log: Common log book object
        :param method: Api Request Method type (PUT/POST)
        :return: common log book object
        """
        try:
            responses = req(instance=instance, path=api_url, method=method, data=data)
        except Exception as error:
            raise UserError(_("Error while Export product stock " + str(error)))
        if responses:
            messages = []
            for response in responses:
                if isinstance(response, dict) and response.get('code') != '200':
                    messages.append((0, 0, {'message': response.get('message'),
                                            'magento_export_stock_queue_line_id': line.id}))
            if messages:
                log.write({'log_lines': messages})
        return True

    def get_magento_product_stock_ept(self, instance, product_ids, warehouse):
        """
        This Method relocates check type of stock.
        :param instance: This arguments relocates instance of amazon.
        :param product_ids: This arguments product listing id of odoo.
        :param warehouse:This arguments relocates warehouse of amazon.
        :return: This Method return product listing stock.
        """
        product = self.env['product.product']
        stock = {}
        if product_ids:
            if instance.magento_stock_field == 'free_qty':
                stock = product.get_free_qty_ept(warehouse, product_ids)
            elif instance.magento_stock_field == 'virtual_available':
                stock = product.get_forecasted_qty_ept(warehouse, product_ids)
            elif instance.magento_stock_field == 'onhand_qty':
                stock = product.get_onhand_qty_ept(warehouse, product_ids)
        return stock

    def export_magento_stock(self, line, api_url, log):
        instance = line.instance_id
        data = json.loads(line.data)
        if data:
            self.call_export_product_stock_api(instance, api_url, data, log, 'PUT', line)
        return True
