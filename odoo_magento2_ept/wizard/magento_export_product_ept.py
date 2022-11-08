# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes product import export process.
"""
import time
import logging
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from ..models.api_request import req
from ..python_library.php import Php

_logger = logging.getLogger("MagentoEPT")


class MagentoExportProductEpt(models.TransientModel):
    """
    Describes Magento Process for import/ export operations
    """
    _name = 'magento.export.product.ept'
    _description = 'Magento Export Product Ept'

    magento_instance_ids = fields.Many2many('magento.instance', string="Instances",
                                            help="This field relocates Magento Instance")
    attribute_set_id = fields.Many2one('magento.attribute.set', string='Attribute Set',
                                       help="Magento Attribute Sets")
    is_set_image = fields.Boolean(string="Set Image ?", default=False)
    is_set_price = fields.Boolean(string="Set Price ?", default=False)
    update_price = fields.Boolean(string="Update Price ?", default=False)
    m_update_image = fields.Boolean(string="Update Image ?", default=False)
    magento_publish = fields.Selection([('publish', 'Publish'), ('unpublish', 'Unpublish')],
                                       string="Publish In Website ?",
                                       help="If select publish then Publish the product in website "
                                            "and If the select unpublish then Unpublish the "
                                            "product from website")
    m_update_basic_details = fields.Boolean(string="Update Basic Details ?", default=False)
    m_update_description = fields.Boolean(
        string="Update Product Description/Short Description ?", default=False)
    description_config_value = fields.Boolean(string="Allow Product Description/Short Description?")

    @api.model
    def default_get(self, field_list):
        """
        based on the global configuration of the sale description set
        the value in description_config_value
        :param field_list:
        :return:
        """
        res = super(MagentoExportProductEpt, self).default_get(field_list)
        global_product_description = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_magento2_ept.set_magento_sales_description")
        res.update({'description_config_value': global_product_description})

        return res

    @api.onchange('attribute_set_id')
    def onchange_attribute_set_id(self):
        """
        Set domain for site ids when change attribute sets.
        """
        m_template = self.env['magento.product.template']
        attribute_sets = self.env['magento.attribute.set']
        m_template_ids = self.env.context.get('active_ids', [])
        if m_template_ids:
            m_template = m_template.search([('id', 'in', m_template_ids)])
            instances = m_template.mapped('magento_instance_id')
            attribute_sets = attribute_sets.search([('instance_id', 'in', instances.ids)])
        return {'domain': {'attribute_set_id': [('id', 'in', attribute_sets.ids)]}}

    def process_export_products_in_magento(self):
        """
        export new product in magento
        :return:
        """
        template_ids = self.env.context.get('active_ids', [])
        self.__do_verification()
        instance = self.env['magento.instance']
        instances = instance.search([])
        log_ids = []
        for instance in instances:
            m_templates = self.__find_magento_templates(template_ids, instance, False)
            if not m_templates:
                continue
            log = instance.create_log_book('magento.product.template', 'export')
            for m_template in m_templates:
                attribute_set_id = self.attribute_set_id if self.attribute_set_id else m_template.attribute_set_id
                if attribute_set_id:
                    self.export_simple_product(instance, m_template, attribute_set_id, log)
                    self.export_configurable_product(instance, m_template, attribute_set_id,
                                                     log)
            if log and not log.log_lines:
                log.unlink()
            else:
                log_ids.append(log.id)
        if log_ids:
            return {
                'name': 'Export Product Log',
                'type': 'ir.actions.act_window',
                'res_model': 'common.log.book.ept',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', log_ids)],
            }

        return {
            'effect': {
                'fadeout': 'slow',
                'message': " 'Export Product(s) in Magento' Process Completed Successfully! {}".format(
                    ""),
                'img_url': '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def export_simple_product(self, instance, m_template, attribute_set_id, common_log_id):
        """
        Export simple product in magento
        :param instance: Magento Instance
        :param m_template: Simple product template
        :param attribute_set_id: Under which attribute set create a simple product ?
        :param common_log_id: Log book ID
        :return:
        """
        product_tmpl = m_template.filtered(
            lambda x: x.product_type == 'simple' and not x.sync_product_with_magento)
        if product_tmpl:
            for product in product_tmpl:
                _logger.info("start create new simple product : %s ", product.magento_sku)
                self.create_product_in_magento(
                    instance, product, attribute_set_id, common_log_id, product_type='simple')
        return True

    def export_configurable_product(self, instance, m_template, attribute_set_id,
                                    common_log_id):
        """
        Export Configurable product in odoo
        :param instance: Instance record
        :param m_template: Configurable product template
        :param attribute_set_id: Under which attribute set create the product?
        :param common_log_id: log book ID
        :return:
        """
        magento_product_obj = self.env['magento.product.template']
        product_tmpl = m_template.filtered(
            lambda x: x.product_type == 'configurable' and not x.sync_product_with_magento)
        if product_tmpl:
            for product in product_tmpl:
                _logger.info("start create new configurable product name : %s ", product)
                self.create_product_in_magento(instance, product, attribute_set_id, common_log_id,
                                               product_type='configurable')
                if product.attribute_line_ids:
                    conf_product_sku = product.magento_product_name
                    configurable_opt_vals = magento_product_obj.prepare_configurable_option_vals(
                        conf_product_sku, common_log_id, instance, product, attribute_set_id)
                    if configurable_opt_vals:
                        continue
                    self.__find_attribute_for_product(product, instance, attribute_set_id,
                                                      common_log_id)
                    magento_product_obj.bind_simple_with_configurable_product(
                        instance,
                        product.magento_product_ids.mapped(
                            'magento_sku'),
                        conf_product_sku,
                        common_log_id)
        return True

    def __find_attribute_for_product(self, product, instance, attribute_set_id, common_log_id):
        """
        This method used for find attribute for product
        :param product:
        :return:
        """
        for product_product in product.magento_product_ids:
            if product_product.product_template_attribute_value_ids:
                self.fine_product_attributes(product_product, instance,
                                             attribute_set_id,
                                             common_log_id)

    def __do_verification(self):
        '''
        This method is use for varify all constraint for export product
        :return: raise waring
        '''
        magento_template_ids = self.env.context.get('active_ids', [])
        if not self.is_set_price and not self.magento_publish and \
                not self.is_set_image and not self.attribute_set_id:
            raise UserError(_("Please select any of the above operation to export product"))

        if not magento_template_ids:
            raise UserError(_("Please select some products to Export to Magento Store."))

        if magento_template_ids and len(magento_template_ids) > 80:
            raise UserError(_("Error:\n- System will not export more then 80 Products at a "
                              "time.\n- Please select only 80 product for export."))
        return True

    def __do_update_verification(self):
        '''
        This method is use for varify all constraint for update product
        :return: raise waring
        '''
        update_ids = self.env.context.get('active_ids', [])
        update_img = self.m_update_image
        update_price = self.update_price
        basic_details = self.m_update_basic_details
        update_description = self.m_update_description

        if not update_img and not update_price and not basic_details and not update_description:
            raise UserError(_("Please select any of the above operation to update the product."))

        if not update_ids:
            raise UserError(_("Please select some products to Update in Magento Store."))

        if update_ids and len(update_ids) > 80:
            raise UserError(_("Error:\n- System will not update more then 80 Products at a "
                              "time.\n- Please select only 50 product for update."))
        return True

    def process_update_products_in_magento(self):
        """
        update existing product in magento
        :return:
        """
        self.__do_update_verification()
        update_ids = self.env.context.get('active_ids', [])
        magento_instance_obj = self.env['magento.instance']
        instances = magento_instance_obj.search([])
        log = []
        for instance in instances:
            common_log = instance.create_log_book('magento.product.template', 'export')
            self.__find_not_synced_m_templates(instance, update_ids, common_log)
            m_templates = self.__find_magento_templates(update_ids, instance)
            if m_templates:
                start = time.time()
                self.__update_simple_product(instance, m_templates, common_log)
                self.__update_configurable_product(instance, m_templates, common_log)
                end = time.time()
                _logger.info("Updated total templates  %s  in %s seconds.", len(m_templates),
                             str(end - start))
            if common_log and not common_log.log_lines:
                common_log.unlink()
            else:
                log.append(common_log.id)
        if log:
            return {
                'name': 'Update Product Log',
                'type': 'ir.actions.act_window',
                'res_model': 'common.log.book.ept',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', log)],
            }

        return {
            'effect': {
                'fadeout': 'slow',
                'message': " 'Export Product(s) in Magento' Process Completed Successfully! {}".format(
                    ""),
                'img_url': '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def __find_not_synced_m_templates(self, instance, update_ids, log):
        m_template_obj = self.env['magento.product.template']
        m_templates = m_template_obj.search([
            ('id', 'in', update_ids), ('sync_product_with_magento', '=', False),
            ('magento_instance_id', '=', instance.id)])
        for magento_tmpl in m_templates:
            log.write({
                'log_lines': [(0, 0, {
                    'message': 'You were trying to update the Product. But still,'
                               ' this product was not created in Magento. '
                               'Please Perform the "Export Product In Magento" Operation first for this Product.',
                    'default_code': magento_tmpl.magento_sku
                })]
            })
        return True

    def __update_simple_product(self, instance, m_templates, log):
        product_tmpl = m_templates.filtered(lambda x: x.product_type == 'simple')
        for simple_product in product_tmpl:
            self.__update_product(instance, simple_product, log)
        return True

    def __update_configurable_product(self, instance, m_templates, log):
        product_tmpl = m_templates.filtered(lambda x: x.product_type == 'configurable')
        if len(product_tmpl) > 0:
            for conf_product in product_tmpl:
                website_ids = m_templates.get_magento_website_ids(instance, conf_product)
                for website_id in website_ids:
                    product_dict = self.__prepare_conf_product_dict(conf_product, log, website_id)
                    api_url = '/all/V1/products/%s' % Php.quote_sku(conf_product.magento_sku)
                    self.env['magento.product.template'].update_product_request(instance, product_dict,
                                                                                api_url)
                for m_variant in conf_product.magento_product_ids:
                    self.__update_product(instance, m_variant, log, True)
        return True

    def __prepare_conf_product_dict(self, m_template, log, website_id):
        product_dict = {}
        if m_template.magento_product_ids:
            product_dict = self.__prepare_update_conf_product_dict(m_template, log, is_child=False)
            descriptions = self.__find_descriptions(m_template)
            product_dict.get('product').update({'custom_attributes': descriptions})
            if self.m_update_image or self.m_update_description or self.m_update_basic_details:
                product_dict = self.__prepare_images_dict(product_dict, m_template)
        return product_dict

    def __update_product(self, instance, m_template, log, is_child=False):
        m_template_obj = self.env['magento.product.template']
        m_product = m_template if not is_child else m_template.magento_tmpl_id
        website_ids = m_template_obj.get_magento_website_ids(instance, m_product)
        if website_ids:
            for website_id in website_ids:
                product_dict = self.__prepare_update_product_dict(m_template, log, is_child, website_id)
                if self.m_update_basic_details:
                    website_ids_dict = [int(magento_website_id) for magento_website_id in
                                        website_ids.mapped(
                                            'magento_website_id')]
                    product_dict.get('product').get('extension_attributes').update(
                        {'website_ids': website_ids_dict})
                product = m_product if is_child else m_template
                descriptions = self.__find_descriptions(product)
                m_store_view = self.__find_store_view(website_id)
                self.__update_product_in_magento(instance, m_template, m_store_view, descriptions,
                                                 product_dict)
                product_dict.get('product').update({'name': m_template.magento_product_name})
                product_dict = self.__prepare_images_dict(product_dict, m_template, is_child)
                api_url = '/all/V1/products/%s' % Php.quote_sku(m_template.magento_sku)
                self.env['magento.product.template'].update_product_request(instance, product_dict,
                                                                            api_url)
            price_dict = self.__update_product_website_vise(instance, website_ids, product,
                                                            product_dict)
            self.__update_product_price_in_magento(instance, m_template, price_dict, log)
        else:
            log.write({
                'log_lines': [(0, 0, {
                    'message': "Not set any website in the product : %s" % m_template.magento_product_name,
                    'default_code': m_template.magento_sku
                })]
            })
        return True

    def __find_store_view(self, m_website):
        magento_storeview = self.env['magento.storeview'].search(
            [('magento_website_id', 'in', m_website.ids)])
        return magento_storeview

    def __find_m_categories(self, product, is_child=False):
        if is_child:
            category_ids = product.magento_tmpl_id.category_ids
        else:
            category_ids = product.category_ids
        categories = []
        if category_ids and self.m_update_basic_details or self.magento_publish in ['publish',
                                                                                    'unpublish']:
            for cat in category_ids:
                val = {"position": 0, "category_id": cat.category_id}
                categories.append(val)
        return categories

    def __find_tax_class(self, product, is_child=False):
        tax_dict = False
        # self.m_update_basic_details in this condition this variable used when update product
        # and if its true then tax class with apply
        # self.magento_publish this variable used when export product
        if not is_child and product.magento_tax_class and \
                self.m_update_basic_details or self.magento_publish in ['unpublish', 'publish']:
            tax_dict = {
                "attribute_code": "tax_class_id",
                "value": product.magento_tax_class.magento_tax_class_id
            }
        return tax_dict

    def __find_cost_price(self, product, log, is_child, website_id):
        """
        Find cost price on pricelist otherwise product cost price set
        :param product: Product object
        :param log: Log book object
        :param is_child: True or False
        :param website_id: website object
        :return: cost price dictionary
        """
        m_template_obj = self.env['magento.product.template']
        cost_dict = False
        if is_child:
            m_instance = product.magento_tmpl_id.magento_instance_id
            m_product = product
        else:
            m_instance = product.magento_instance_id
            m_product = product.magento_product_ids
        product_cost_price = m_template_obj.get_scope_wise_product_price(
            m_instance, log, m_product, website_id.cost_pricelist_id, cost_price=True)
        if product_cost_price and self.update_price or self.magento_publish in ['publish',
                                                                                    'unpublish']:
            cost_dict = {
                "attribute_code": "cost",
                "value": product_cost_price
            }
        return cost_dict

    def __find_descriptions(self, product):
        custom_attributes = []
        description = product.description
        sale_description_export = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_magento2_ept.set_magento_sales_description')
        if sale_description_export and self.m_update_description:
            if description:
                values = {
                    "attribute_code": "description",
                    "value": description
                }
                custom_attributes.append(values)

            if 'short_description' in product:
                description_sale = product.short_description
                short_description = {
                    "attribute_code": "short_description",
                    "value": description_sale
                }
                custom_attributes.append(short_description)
        return custom_attributes

    def __prepare_update_product_dict(self, m_template, log, is_child, website_id):
        categories = self.__find_m_categories(m_template, is_child)
        tax_class = self.__find_tax_class(m_template, is_child)
        cost_price = self.__find_cost_price(m_template, log, is_child, website_id)
        update_product_dict = {
            "product": {
                "name": m_template.magento_product_name,
                "extension_attributes": {
                },
                "custom_attributes": []
            }
        }
        if categories:
            update_product_dict.get('product').get('extension_attributes').update(
                {'category_links': categories})
        if tax_class:
            update_product_dict.get('product').get('custom_attributes').append(tax_class)
        if cost_price:
            update_product_dict.get('product').get('custom_attributes').append(cost_price)
        return update_product_dict

    def __prepare_update_conf_product_dict(self, m_template, log, is_child):
        categories = self.__find_m_categories(m_template, is_child)
        tax_class = self.__find_tax_class(m_template, is_child)
        update_product_dict = {
            "product": {
                "name": m_template.magento_product_name,
                "extension_attributes": {
                },
                "custom_attributes": []
            }
        }
        if categories:
            update_product_dict.get('product').get('extension_attributes').update(
                {'category_links': categories})
        if tax_class:
            update_product_dict.get('product').get('custom_attributes').append(tax_class)
        return update_product_dict

    def __update_product_website_vise(self, instance, website_ids, product, product_dict):
        price_dict = []
        for website in website_ids:
            m_store_view = self.__find_store_view(website)
            price_dict = self.__prepare_update_website_price_dict(
                instance, website, m_store_view, product, price_dict)
        return price_dict

    def __update_product_in_magento(self, instance, product, m_store_view, custom_attrs,
                                    product_dict):
        if m_store_view:
            for store_view in m_store_view:
                # convert description and short description with store view lang.
                if custom_attrs:
                    product_dict = self.env['magento.product.template'].translate_description(
                        product_dict, store_view, custom_attrs, product)
                api_url = '/%s/V1/products/%s' % (
                    store_view.magento_storeview_code,
                    Php.quote_sku(product.magento_sku))
                _logger.info("Store code %s", store_view.lang_id.code)
                self.env['magento.product.template'].update_product_request(
                    instance, product_dict, api_url)

    def __prepare_product_price_dict(self, price_list, m_template, store_view_id):
        is_it_child = False
        m_product = self.env['magento.product.template'].get_simple_product(is_it_child,
                                                                            m_template)
        product_price = price_list. \
            get_product_price(m_product.odoo_product_id,
                              price_list.id, False)
        _logger.info("%s : in product.product price is : %s" % (
            m_product.odoo_product_id.name, product_price))
        price_vals = {"sku": m_template.magento_sku, "price": product_price,
                      "store_id": store_view_id}
        return price_vals

    def __prepare_update_website_price_dict(self, instance, website, m_store_view, m_template,
                                            price_dict):
        if self.update_price and instance.catalog_price_scope == 'website' and m_store_view:
            currency = website.magento_base_currency.id
            for store_view in m_store_view:
                pricelist = website.pricelist_ids.filtered(lambda x: x.currency_id.id == currency)
                if pricelist:
                    pricelist = pricelist[0]
                    price_vals = self.__prepare_product_price_dict(
                        pricelist, m_template, store_view.magento_storeview_id)
                    price_dict.append(price_vals)
        return price_dict

    def __update_product_price_in_magento(self, instance, m_template, price_dict, log):
        if self.update_price:
            if instance.catalog_price_scope == 'global':
                _logger.info("Instance %s price scope is Global. ", instance.name)
                if instance.pricelist_id:
                    price_vals = self.__prepare_product_price_dict(
                        instance.pricelist_id, m_template, 0)
                    price_dict.append(price_vals)
                else:
                    log.write({
                        'log_lines': [(0, 0, {
                            'message': "Price scope is Global, "
                                       "But still pricelist not set for the Instance : %s" % instance.name
                        })]
                    })

            if price_dict:
                price_data = {"prices": price_dict}
                price_url = '/V1/products/base-prices'
                self.env['magento.product.template'].update_product_base_price(instance, price_url,
                                                                               log, price_data)
                _logger.info("Price Updated successfully.")

    def __prepare_images_dict(self, product_dict, m_template, is_child=False):
        if self.m_update_image:
            media_gallery = self.env['magento.product.template'].prepare_export_images_values(
                m_template, m_template.product_type, is_child)
            if media_gallery:
                product_dict['product']['media_gallery_entries'] = media_gallery
        return product_dict

    def __find_magento_templates(self, template_ids, instance, status=True):
        """
        Search
        :param instance:
        :return:
        """
        m_templates = self.env['magento.product.template'].search([
            ('id', 'in', template_ids), ('sync_product_with_magento', '=', status)])
        return m_templates.filtered(lambda x: x.magento_instance_id == instance)

    def export_stock_in_magento_ept(self):
        """
        This method are used to export stock in Magento. And it will be called from Multi Action
        Wizard in Magento product tree view.
        :return:
        """
        m_template = self.env['magento.product.template']
        m_product_ids = self.env.context.get('active_ids', [])
        self.magento_export_stock_validation(m_product_ids)
        instances = self.env['magento.instance'].search([])
        logs = list()
        m_templates = m_template.search([('id', 'in', m_product_ids),
                                         ('sync_product_with_magento', '=', True)])
        for instance in instances:
            log = instance.create_common_log_book('export', 'magento.product.template')
            # self.check_sync_magento_product_templates(m_product_ids, instance, log)
            # m_template = self.get_magento_product_template_by_instance(m_templates, instance)
            # if m_template:
            #     product_ids = m_template.magento_product_ids.mapped('odoo_product_id')
            product_ids = m_templates.mapped('magento_product_ids.odoo_product_id').ids
            self.export_product_stock_magento(instance, product_ids, log)
            if log and not log.log_lines:
                log.unlink()
            else:
                logs.append(log.id)
        if logs:
            return {
                'name': 'Export Product Log',
                'type': 'ir.actions.act_window',
                'res_model': 'common.log.book.ept',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', logs)],
            }

        return {
            'effect': {
                'fadeout': 'slow',
                'message': " 'Update Product stocks(s) in Magento' Process Completed Successfully! {}".format(
                    ""),
                'img_url': '/web/static/src/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def magento_create_log_book(self, instance):
        """
        Create Log Book record for export product template.
        :param instance: Magento Instance object
        :return: log book record
        """
        model_id = self.env['common.log.lines.ept'].get_model_id('magento.product.template')
        log_book_id = self.env["common.log.book.ept"].create({
            'type': 'export',
            'module': 'magento_ept',
            'model_id': model_id,
            'magento_instance_id': instance.id
        })
        return log_book_id

    def export_product_stock_operation(self, instance):
        """
        This method calls from Scheduler and Operation Wizard
        :param instance: Magento Instance
        :return:
        """
        log = self.env['common.log.book.ept']
        log_line = self.env['common.log.lines.ept']
        if instance:
            product_ids = self.get_export_products(instance)
            model_id = log_line.get_model_id('magento.product.product')
            log = log.create_common_log_book(process_type='export',
                                             instance_field='magento_instance_id',
                                             instance=instance, model_id=model_id,
                                             module='magento_ept')
            self.export_product_stock_magento(instance, product_ids, log)
            if log and not log.log_lines:
                log.unlink()
            instance.write({'last_update_stock_time': datetime.now()})
            self._cr.commit()
        return True

    @staticmethod
    def magento_export_stock_validation(m_products):
        """
        selected product count check
        :param: products object
        """
        if not m_products:
            raise UserError(_("Please select some products to Update Stock in Magento Store."))

        if m_products and len(m_products) > 80:
            raise UserError(_("Error:\n- System will not update stock more then 80 Products at a "
                              "time.\n- Please select only 80 product for update stock."))
        return True

    def check_sync_magento_product_templates(self, m_products, instance, log):
        """
        filter product template if found any template then set log lines.
        :param: instance: instance object
        :m_products: set multiple product object
        :log : common log
        """
        m_template = self.env['magento.product.template']
        m_templates = m_template.search([
            ('id', 'in', m_products), ('sync_product_with_magento', '=', False),
            ('magento_instance_id', '=', instance.id)])
        for template in m_templates:
            log.write({
                'log_lines': [(0, 0, {
                    'message': 'You were trying to update the Product Stock. But still, '
                               'this product was not created in Magento. '
                               'Please Perform the "Export Product In Magento" '
                               'Operation first for this Product.',
                    'default_code': template.magento_sku
                })]
            })
        return True

    def export_product_stock_magento(self, instance, product_ids, log):
        """
        export product stock in magento with location and multiple warehouse.
        :param: instance: instance object
        :product_ids: set multiple product object
        :log : common log
        """
        layer_ids = self._filter_export_stock_products(instance, product_ids)
        product_ids = [product.get('id') for product in layer_ids]
        if instance.magento_version in ['2.1', '2.2'] or not instance.is_multi_warehouse_in_magento:
            # This condition is checked for verify the Magento version.
            # We only call this method for NON MSI magento versions. If customer using
            # Magento version 2.3+ and not using the MSI functionality then also this method
            # will be called.
            self.export_stock_non_msi(instance, product_ids, log, layer_ids)
        else:
            self.export_stock_with_msi(instance, product_ids, log, layer_ids)
        return True

    def _filter_export_stock_products(self, instance, product_ids):
        m_product = self.env['magento.product.product']
        o_product = self.env['product.product']
        m_products = m_product.search_read([('odoo_product_id', 'in', product_ids),
                                            ('magento_instance_id', '=', instance.id)],
                                           fields=['odoo_product_id', 'magento_sku'])
        datas = []
        o_product = o_product.search_read([('id', 'in', product_ids)], fields=['type'])
        for product in m_products:
            product_id = product.get('odoo_product_id')[0]
            if product.get('magento_sku'):
                p_type = [p.get('type') for p in o_product if p.get('id') == product_id][0]
                datas.append({
                    'id': product.get('odoo_product_id')[0],
                    'magento_sku': product.get('magento_sku'),
                    'type': p_type
                })
        return datas

    def get_export_products(self, instance):
        """
        get Export product ids list based on instance
        last update date based on find out product (common control method used)
        :param: instance: instance object
        return : product list of
        """
        product = self.env['product.product']
        last_date = instance.last_update_stock_time
        if not last_date:
            last_date = datetime.today() - timedelta(days=365)
        product_ids = product.get_products_based_on_movement_date_ept(
            last_date, instance.company_id
        )
        return product_ids

    def export_stock_non_msi(self, instance, product_ids, log, layer_ids):
        """
        single instance warehouse export product stock
        :param: instance: instance object
        :product_ids: set multiple product object
        :log : common log
        """
        m_product = self.env['magento.product.product']
        m_template = self.env['magento.product.template']
        if not instance.warehouse_ids:
            raise UserError(
                _("Please select Export Stock Warehouse for {} instance.").format(instance.name))
        product_stock = m_product.get_magento_product_stock_ept(instance, product_ids,
                                                                instance.warehouse_ids)
        if product_stock:
            stock_data = m_template.prepare_export_stock_data(product_stock=product_stock,
                                                              instance=instance, log=log,
                                                              layer_ids=layer_ids)
            if stock_data:
                api_url = "/V1/product/updatestock"
                m_product.exp_prd_stock_in_batches(stock_data, instance, api_url, 'skuData', 'PUT',
                                                   log)
        return True

    def export_stock_with_msi(self, instance, product_ids, log, layer_ids):
        """
        multiple warehouse export product stock
        :param: instance: instance object
        :product_ids: set multiple product object
        :log : common log
        """
        m_product = self.env['magento.product.product']
        m_template = self.env['magento.product.template']
        locations = self.env['magento.inventory.locations'].search([
            ('magento_instance_id', '=', instance.id), ('active', '=', True)
        ])
        stock_data = list()
        for location in locations:
            stock_locations = location.mapped('export_stock_warehouse_ids')
            if not stock_locations:
                raise UserError(_("Please select Export Stock Warehouse "
                                  "for {} location.").format(location.name))
            product_stock = m_product.get_magento_product_stock_ept(instance, product_ids,
                                                                    stock_locations)
            if product_stock:
                stock_data += m_template.prepare_export_stock_data(product_stock=product_stock,
                                                                   instance=instance,
                                                                   log=log, layer_ids=layer_ids,
                                                                   source_code=location.magento_location_code,
                                                                   msi=True)
        if stock_data:
            api_url = "/V1/inventory/source-items"
            m_product.exp_prd_stock_in_batches(stock_data, instance, api_url, 'sourceItems', 'POST',
                                               log)
        return True

    def create_product_in_magento(self, instance, product, attribute_set_id, log,
                                  product_type='simple', is_it_child=False, custom_attributes=[]):
        """
        Create the simple or configurable product in magento
        :param instance: Magento Instance
        :param product: Product.template
        :param attribute_set_id: Under which Attribute set create a new product ?
        :param common_log_book_id: Log book record
        :param product_type: Product type
        :param is_it_child: Is the product is child of any configurable product
        :param custom_attributes: Custom Attribute array
        :return:
        """
        m_template = self.env['magento.product.template']
        response = False
        conf_custom_attrs = custom_attributes
        custom_attributes = m_template.prepare_main_product_description_array(custom_attributes,
                                                                              product)
        m_product = product if not is_it_child else product.magento_tmpl_id
        website_ids = m_template.get_magento_website_ids(instance, m_product)
        conf_simple_product = m_template.get_simple_product(is_it_child, product, product_type)
        attribute_set = m_template.get_magento_attribute_set(
            product, product_type, is_it_child, attribute_set_id, log)
        data = self.prepare_product_data(product, is_it_child, product_type, attribute_set,
                                         website_ids)
        if conf_custom_attrs:
            for configurable_opt in conf_custom_attrs:
                if (configurable_opt.get('attribute_code') != 'description' and
                        configurable_opt.get('attribute_code') != 'short_description'):
                    data.get('product', dict()).get('custom_attributes').append(configurable_opt)
        if website_ids:
            response = self.__create_product_website_vise(instance,
                                                          conf_simple_product,
                                                          website_ids,
                                                          product, data,
                                                          log, is_it_child)
            website_vals = self.__prepare_website_vise_dict(product, website_ids, custom_attributes,
                                                            product_type, is_it_child)
            self.__set_websites_images_in_magento(instance, product, website_vals,
                                                  log)
        else:
            log.write({
                'log_lines': [(0, 0, {
                    'message': "Website not set in the product template, So we can't create new"
                               "Product in Magento with SKU : %s" % product.magento_sku,
                    'default_code': product.magento_sku
                })]
            })
            return True
        if response:
            m_template.write_product_id_in_odoo(response, product_type, is_it_child, product)
        if not log.log_lines:
            magento_product_images = m_template.get_magento_product_images(product, product_type,
                                                                           is_it_child)
            if magento_product_images:
                self.set_magento_product_image(magento_product_images)
        return True

    def __create_product_website_vise(self, instance, conf_simple_product, website_ids, product,
                                      data, log, is_it_child):
        m_template = self.env['magento.product.template']
        descriptions = self.__find_descriptions(product)
        magento_website_id = []
        export_all = 0
        response = False
        for website in website_ids:
            m_store_view = self.__find_store_view(website)
            product_cost_price = m_template.get_scope_wise_product_price(
                instance, log, conf_simple_product, website.cost_pricelist_id, cost_price=True)
            data.get('product', dict()).get('custom_attributes').append({
                "attribute_code": "cost",
                "value": product_cost_price
            })
            for store in m_store_view:
                price = self.__get_product_price(instance, website, conf_simple_product, log)
                data.get('product').update({'price': price})
                if descriptions:
                    data = m_template.translate_description(
                        data, store, descriptions, product)
                if is_it_child == False:
                    if export_all == 0 and product.export_product_to_all_website:
                        api_url = '/all/V1/products'
                        req(instance, api_url, 'POST', data)
                        export_all = 1
                try:
                    api_url = '/%s/V1/products' % store.magento_storeview_code
                    response = req(instance, api_url, 'POST', data)
                except Exception as error:
                    log.write({
                        'log_lines': [(0, 0, {
                            'message': "%s \nNot able to create new Simple"
                                       " Product in Magento. SKU : %s" % (
                                           error, product.magento_sku),
                            'default_code': product.magento_sku
                        })]
                    })
                    return True
                magento_website_id.append(int(website.magento_website_id))
        return response

    def __prepare_website_vise_dict(self, product, website_id, custom_attributes, product_type,
                                    is_child):
        conf_product_name = product.magento_product_name
        sku = product.magento_sku if product.magento_sku else product.magento_product_name
        data = {
            "product": {
                "sku": sku,
                "name": conf_product_name,
                "extension_attributes": {
                    "website_ids": website_id.mapped('magento_website_id')
                },
                "custom_attributes": custom_attributes
            }
        }
        if self.is_set_image:
            media_gallery = self.env['magento.product.template'].prepare_export_images_values(
                product, product_type, is_child)
            if media_gallery:
                data.get('product', dict()).update({'media_gallery_entries': media_gallery})
        return data

    @staticmethod
    def __set_websites_images_in_magento(instance, product, data, log):
        sku = product.magento_sku if product.magento_sku else product.magento_product_name
        try:
            api_url = '/all/V1/products/%s' % Php.quote_sku(sku)
            req(instance, api_url, 'PUT', data)
        except Exception:
            log.write({
                'log_lines': [(0, 0, {
                    'message': "Website can not able to assign in product SKU : %s in magento" % sku,
                    'default_code': sku
                })]
            })
        return True

    def __get_product_price(self, instance, website, m_template, log):
        m_template_obj = self.env['magento.product.template']
        product_price = 0
        currency = website.magento_base_currency.id
        if self.is_set_price:
            if instance.catalog_price_scope == 'global':
                product_price = m_template_obj.get_scope_wise_product_price(
                    instance, log, m_template, instance.pricelist_id)
            else:
                price_list = website.pricelist_ids.filtered(lambda x: x.currency_id.id == currency)
                if price_list:
                    price_list = price_list[0]
                    product_price = m_template_obj.get_scope_wise_product_price(instance, log,
                                                                                m_template,
                                                                                price_list)
        return product_price

    def set_magento_product_image(self, magento_product_images):
        for magento_product_image in magento_product_images:
            magento_product_image.write({'exported_in_magento': True})

    def prepare_product_data(self, product, is_child, product_type, attribute_set, website_ids):
        main_product_tmpl = product if not is_child else product.magento_tmpl_id
        sku = product.magento_sku if product.magento_sku else product.magento_product_name
        categories = self.__find_m_categories(product, is_child)
        tax_class = self.__find_tax_class(main_product_tmpl, is_child)
        data = {
            "product": {
                "sku": sku,
                "name": product.magento_product_name,
                "attribute_set_id": attribute_set,
                "status": 1 if self.magento_publish == "publish" else 0,
                "visibility": 4 if not is_child else 1,
                "type_id": product_type,
                "extension_attributes": {
                    "website_ids": website_ids.mapped('magento_website_id'),
                },
                "custom_attributes": []
            }
        }
        if categories:
            data.get('product').get('extension_attributes').update({'category_links': categories})
        if tax_class.get('value'):
            data.get('product', dict()).get('custom_attributes').append(tax_class)
        return data

    def fine_product_attributes(self, o_product, instance, attribute_set_id,
                                common_log_id):
        '''
        This method used for find attributes and create product in magento.
        :param o_product:
        :param instance:
        :param attribute_set_id:
        :param common_log_id:
        :return:
        '''
        vals = []
        magento_attribute_obj = self.env['magento.product.attribute']
        magento_attribute_option_obj = self.env['magento.attribute.option']
        for value_id in o_product.product_template_attribute_value_ids:
            magento_attribute_option = magento_attribute_option_obj.search([
                ('instance_id', '=', instance.id),
                ('odoo_option_id', '=', value_id.product_attribute_value_id.id)
            ], limit=1)
            magento_attribute = magento_attribute_obj. \
                browse(magento_attribute_option.magento_attribute_id.id)
            if not magento_attribute_option or not magento_attribute:
                _logger.info("%s attribute option or its value still not sync with odoo."
                             , value_id.product_attribute_value_id.name)
                break
            attribute_code = magento_attribute.magento_attribute_code
            attribute_val = {
                "attribute_code": attribute_code.lower(),
                "value": magento_attribute_option.magento_attribute_option_id
            }
            o_product.magento_product_name = "{} - {}".format(o_product.magento_product_name,
                                                              magento_attribute_option.magento_attribute_option_name)
            vals.append(attribute_val)
        self.create_product_in_magento(instance, o_product, attribute_set_id, common_log_id,
                                       product_type='simple',
                                       is_it_child=True,
                                       custom_attributes=vals)
        return True
