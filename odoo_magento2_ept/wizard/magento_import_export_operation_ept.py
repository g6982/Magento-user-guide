# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes product import export process.
"""
import base64
import csv
import xlrd
import io
import os
from csv import DictWriter
from io import StringIO
from datetime import datetime, timedelta
from odoo.tools.misc import xlsxwriter
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
MAGENTO_ORDER_DATA_QUEUE_EPT = 'magento.order.data.queue.ept'
IR_ACTION_ACT_WINDOW = 'ir.actions.act_window'
IR_MODEL_DATA = 'ir.model.data'
VIEW_MODE = 'tree,form'
COMPLETED_STATE = "[('state', '!=', 'completed' )]"
IMPORT_MAGENTO_PRODUCT_QUEUE = 'sync.import.magento.product.queue'
MAGENTO_PRODUCT_PRODUCT = 'magento.product.product'


class MagentoImportExportEpt(models.TransientModel):
    """
    Describes Magento Process for import/ export operations
    """
    _name = 'magento.import.export.ept'
    _description = 'Magento Import Export Ept'

    magento_instance_id = fields.Many2one('magento.instance', string="Instance",
                                           help="This field relocates Magento Instance")
    operations = fields.Selection([
        ('map_products', 'Map Products'),
        ('import_configurable_products', 'Import Configurable Products'),
        ('import_simple_products', 'Import Simple Products'),
        ('export_product_stock', 'Export Stock'),
        ('export_shipment_information', 'Export Shipment Information'),
        ('import_ship_sale_order', 'Import Shipped Orders'),
        ('import_unship_sale_order', 'Import Unshipped Orders'),
        ('import_cancel_orders', 'Import Cancel Orders'),
        ('import_product_stock', 'Import Stock'),
        ('import_customer', 'Import Customers'),
        ('import_product_categories', 'Import Categories'),
        ('import_product_attributes', 'Import Attributes'),
        ('import_specific_product', 'Import Specific Product(s)'),
        ('import_specific_order', 'Import Specific Order(s)'),
        ('export_invoice_information', 'Export Invoice Information'),
        ('import_product_taxclass', 'Import Product TaxClass')
    ], string='Operations', help='Import/ Export Operations')

    auto_validate_stock = fields.Boolean(
        string="Auto validate inventory?",
        help="If checked then all product stock will automatically validate"
    )
    start_date = fields.Datetime(string="From Date", help="From date.")
    end_date = fields.Datetime("To Date", help="To date.")
    import_specific_sale_order = fields.Char(
        string="Sale Order Reference",
        help="You can import Magento Order by giving order number here,Ex.000000021 \n "
             "If multiple orders are there give order number comma (,) seperated "
    )
    import_specific_product = fields.Char(
        string='Product Reference',
        help="You can import Magento prduct by giving product sku here, Ex.24-MB04 \n "
             "If Multiple product are there give product sku comma(,) seperated"
    )
    datas = fields.Binary(string="Choose File")
    file_name = fields.Char(string='Name')
    is_import_shipped_orders = fields.Boolean(
        string="Import Shipped Orders?",
        help="If checked, Shipped orders will be imported"
    )
    export_method = fields.Selection([
        ("direct", "Export in Magento Layer"), ("csv", "Export in CSV file"),
        ("xlsx", "Export in XLSX file")
    ], default="csv")
    do_not_update_existing_product = fields.Boolean(
        string="Do not update existing Products?",
        help="If checked and Product(s) found in odoo/magento layer, then not update the Product(s)"
    )

    @api.onchange('operations')
    def on_change_operation(self):
        """
        Set end date when change operations
        """
        if self.operations in ["import_configurable_products", "import_simple_products", "import_sale_order", "import_customer"]:
            self.start_date = datetime.today() - timedelta(days=10)
            self.end_date = datetime.now()
        else:
            self.start_date = None
            self.end_date = None

    def execute(self):
        """
        Execute different Magento operations based on selected operation,
        """
        account_move = self.env['account.move']
        picking = self.env['stock.picking']
        product_attribute = self.env['magento.attribute.set']
        message = ''
        instance = self.magento_instance_id
        result = False
        if self.operations == 'import_customer':
            result = self.import_customer_operation(instance)
        elif self.operations == 'map_products':
            self.map_product_operation(instance)
        elif self.operations in ['import_unship_sale_order', 'import_ship_sale_order']:
            result = self.import_sale_order_operation(instance)
        elif self.operations == 'import_cancel_orders':
            result = self.import_cancel_order_operation(instance)
        elif self.operations == 'import_specific_order':
            result = self.import_specific_sale_order_operation(instance)
        elif self.operations == 'import_configurable_products':
            p_type = 'configurable'
            result = self.import_products_operation(instance, p_type)
        elif self.operations == 'import_simple_products':
            p_type = 'simple'
            result = self.import_products_operation(instance, p_type)
        elif self.operations == 'import_specific_product':
            result = self.import_specific_product_operation(instance)
        elif self.operations == 'import_product_stock':
            result = self.import_product_stock_operation(instance)
        elif self.operations == 'import_product_taxclass':
            tax_class = self.env['magento.tax.class']
            tax_class.import_magento_tax_class(instance)
        elif self.operations == 'import_product_categories':
            self.env['magento.product.category'].get_all_category(instance)
        elif self.operations == 'import_product_attributes':
            product_attribute.import_attribute_set(instance)
        elif self.operations == 'export_shipment_information':
            pickings = picking.search_magento_pickings(instance=instance)
            # We have already handled the loop structure in the method.
            pickings.magento_send_shipment()
        elif self.operations == 'export_invoice_information':
            account_move.export_invoices_to_magento(instance)
        elif self.operations == 'export_product_stock':
            self.env['magento.export.product.ept'].export_product_stock_operation(instance)
        if not result:
            title = [vals for key, vals in self._fields['operations'].selection if
                     key == self.operations]
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': " {} Process Completed Successfully! {}".format(title[0], message),
                    'img_url': '/web/static/src/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        return result

    def map_product_operation(self, instance):
        """
        Perform map product operation.
        :param instance: Magento instance
        """
        if not self.datas:
            raise UserError(_("Please Upload File to Continue Mapping Products..."))
        if os.path.splitext(self.file_name)[1].lower() not in ['.csv', '.xls', '.xlsx']:
            raise ValidationError(
                _("Invalid file format. You are only allowed to upload .csv, .xls or .xlsx "
                  "file."))
        if os.path.splitext(self.file_name)[1].lower() == '.csv':
            self.import_magento_csv(instance)
        else:
            self.import_magento_xls(instance)

    def import_customer_operation(self, instance):
        """
        Create queue of imported customers.
        :param instance: Magento instance
        """
        queue_ids = list()
        queue = self.env['magento.customer.data.queue.ept']
        kwargs = {'from_date': self.start_date, 'to_date': self.end_date}
        if instance:
            kwargs.update({'instance': instance})
            queue_ids += queue.create_customer_queues(**kwargs)
        action = 'odoo_magento2_ept.view_magento_customer_data_queue_ept_form'
        model = 'magento.customer.data.queue.ept'
        return self.env['magento.instance'].get_queue_action(ids=queue_ids, name="Customer Queues",
                                                             model=model,
                                                             action=action)

    def import_cancel_order_operation(self, instance):
        """
        Import cancel sale orders
        :param instance: Magento Instance
        :return:
        """
        kwargs = {'from_date': self.start_date, 'to_date': self.end_date}
        sale_order = self.env['sale.order']
        kwargs.update({'status': 'canceled'})
        if instance:
            kwargs.update({'instance': instance})
            sale_order.import_cancel_order(**kwargs)
        return True

    def import_sale_order_operation(self, instance):
        """
        Create queue of imported sale orders
        :param instance: Magento Instance
        :return:
        """
        queue_ids = list()
        queue = self.env['magento.order.data.queue.ept']
        kwargs = {'from_date': self.start_date, 'to_date': self.end_date}
        if instance:
            if self.operations == 'import_ship_sale_order':
                kwargs.update({'status': 'complete'})
            else:
                kwargs.update({'status': instance.import_magento_order_status_ids.mapped('status')})
            kwargs.update({'instance': instance})
            queue_ids += queue.create_order_queues(**kwargs)
        action = 'odoo_magento2_ept.view_magento_order_data_queue_ept_form'
        model = 'magento.order.data.queue.ept'
        return self.env['magento.instance'].get_queue_action(ids=queue_ids, name="Order Queues",
                                                             model=model,
                                                             action=action)

    def import_specific_sale_order_operation(self, instance):
        """
        Create queue of imported specific order.
        :param instance: Magento Instance
        :return:
        """
        if not self.import_specific_sale_order:
            raise UserError(_("Please enter Magento sale "
                              "order Reference for performing this operation."))
        queue = self.env['magento.order.data.queue.ept']
        queue_ids = list()
        sale_order_list = self.import_specific_sale_order.split(',')
        if instance:
            queue_ids += queue.import_specific_order(instance, sale_order_list)
        action = 'odoo_magento2_ept.view_magento_order_data_queue_ept_form'
        model = 'magento.order.data.queue.ept'
        return self.env['magento.instance'].get_queue_action(ids=queue_ids, name="Order Queues",
                                                             model=model,
                                                             action=action)

    def import_products_operation(self, instance, p_type):
        """
        Create queues of imported products
        :param instance: Magento Instance
        :return:
        """
        queue = self.env['sync.import.magento.product.queue']
        queue_ids = list()
        from_date = datetime.strftime(self.start_date, MAGENTO_DATETIME_FORMAT)
        to_date = datetime.strftime(self.end_date, MAGENTO_DATETIME_FORMAT)
        is_update = self.do_not_update_existing_product
        if instance:
            queue_ids += queue.create_product_queues(instance, from_date, to_date, p_type, is_update,
                                                     current=1)
        model = 'sync.import.magento.product.queue'
        action = 'odoo_magento2_ept.view_sync_import_magento_product_queue_ept_form'
        return self.env['magento.instance'].get_queue_action(ids=queue_ids, name="Product Queues",
                                                             model=model,
                                                             action=action)

    def import_specific_product_operation(self, instance):
        """
        Create queue of imported specific product
        :param instance: Magento Instance
        :return:
        """
        if not self.import_specific_product:
            raise UserError(_("Please enter Magento product"
                              " SKU for performing this operation."))
        queues = list()
        product_queue = self.env[IMPORT_MAGENTO_PRODUCT_QUEUE]
        product_sku_lists = self.import_specific_product.split(',')
        is_update = self.do_not_update_existing_product
        if instance:
            queues = product_queue.import_specific_product(instance, product_sku_lists, is_update)
        action = 'odoo_magento2_ept.view_sync_import_magento_product_queue_ept_form'
        model = 'sync.import.magento.product.queue'
        return self.env['magento.instance'].get_queue_action(ids=queues, name="Product Queues",
                                                             model=model,
                                                             action=action)

    def import_product_stock_operation(self, instance):
        """
        Create inventory adjustment lines of imported product stock.
        :param instance: Magento Instance
        :return:
        """
        m_locations = self.env['magento.inventory.locations']
        m_product = self.env['magento.product.product']
        is_log_exist = False
        if instance:
            if not instance.is_import_product_stock:
                raise UserError(_("You are trying to import product stock."
                                  "But your configuration for the imported stock is disabled for this instance."
                                  "Please enable it and try it again."))
            if instance.magento_version in ['2.1',
                                            '2.2'] or not instance.is_multi_warehouse_in_magento:
                # This condition is checked for verify the Magento version.
                # We only call this method for NON MSI magento versions. If customer using
                # Magento version 2.3+ and not using the MSI functionality then also this method
                # will be called.
                is_log_exist = m_product.import_product_inventory(instance,
                                                                  self.auto_validate_stock)
            else:
                locations = m_locations.search([('magento_instance_id', '=', instance.id)])
                is_log_exist = m_product.import_product_multi_inventory(instance,
                                                                        locations,
                                                                        self.auto_validate_stock)
        if is_log_exist:
            view_ref = self.env.ref('common_connector_library.action_common_log_book_ept_form').id
            return {
                'name': _('Magento Product Import Stock'),
                'res_model': 'common.log.book.ept',
                'type': 'ir.actions.act_window',
                'views': [(view_ref or False, 'form')],
                'view_mode': 'form',
                'view_id': view_ref,
                'res_id': is_log_exist.id,
                'target': 'current'
            }
        else:
            return {
                'name': _('Magento Product Inventory Adjustments'),
                'res_model': 'stock.quant',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
            }

    def prepare_selected_product(self):
        """
        Prepare selected product list and without service type product.
        Then checking list count min one else set message.
        :Return variants : multiple product browse object.
        """
        template_ids = self._context.get("active_ids", [])
        templates = self.env["product.template"].browse(template_ids)
        templates = templates.filtered(lambda template: template.type != "service")
        if not templates:
            raise UserError(_("It seems like selected products are not storable products."))
        variants = templates.product_variant_ids.filtered(
            lambda variant: variant.default_code and len(variant.product_variant_ids.ids) >= 1)
        if not variants:
            raise UserError(_('No data found to be exported.\n\n'
                              'Possible Reasons:\n'
                              '- SKU(s) are not set properly.'))
        return variants

    def prepare_product_for_export_in_magento(self):
        """
        This method is used to export products in Magento layer as per selection.
        If "direct" is selected, then it will direct export product into Magento layer.
        If "xlsx/csv" is selected, then it will export product data in CSV file/xlsx file,
        if user want to do some modification in name, description, etc.
        before importing into Magento.
        """
        variants = self.prepare_selected_product()
        if self.export_method == "direct":
            self.prepare_product_for_magento(variants)
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': " 'Export in Magento Layer' Process Completed Successfully!",
                    'img_url': '/web/static/src/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        else:
            return self.export_product_file_create(variants)

    def export_product_file_create(self, variants):
        """
        Create and download CSV file for export product in Magento.
        :param variants: Odoo product product object
        """
        data = str()
        variants_val = []
        if self.export_method:
            if self.magento_instance_id:
                for variant in variants:
                    val = self.prepare_data_for_export_to_csv_ept(variant, self.magento_instance_id)
                    variants_val.append(val)
            # Based on customer's selected file format apply to call method
            method_name = "_export_{}".format(self.export_method)
            if hasattr(self, method_name):
                data = getattr(self, method_name)(variants_val)
        self.write({'datas': data.get('file')})
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=magento.import.export.ept&'
                   'field=datas&id={}&filename={}'.format(self.id, data.get('file_name')),
            'target': 'self',
        }

    def _export_csv(self, products):
        """
        This method use for export selected product in CSV file for Map product
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        """
        buffer = StringIO()
        csv_writer = DictWriter(buffer, list(products[0].keys()), delimiter=',')
        csv_writer.writer.writerow(list(products[0].keys()))
        csv_writer.writerows(products)
        buffer.seek(0)
        file_data = buffer.read().encode("utf-8")
        b_data = base64.b64encode(file_data)
        filename = 'magento_product_export_{}_{}.csv'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    def _export_xlsx(self, products):
        """
        This method use for export selected product in CSV file for Map product
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param products: Selected product listing ids
        :return: selected product data and file name
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Map Product')
        header = list(products[0].keys())
        header_format = workbook.add_format({'bold': True, 'font_size': 10})
        general_format = workbook.add_format({'font_size': 10})
        worksheet.write_row(0, 0, header, header_format)
        index = 0
        for product in products:
            index += 1
            worksheet.write_row(index, 0, list(product.values()), general_format)
        workbook.close()
        b_data = base64.b64encode(output.getvalue())
        filename = 'magento_product_export_{}_{}.xlsx'.format(self.id, datetime.now().strftime(
            "%m_%d_%Y-%H_%M_%S"))
        return {'file': b_data, 'file_name': filename}

    @staticmethod
    def prepare_data_for_export_to_csv_ept(variant, instance):
        """
        Prepare data for Export Operations at map Odoo Products csv with Magento Products.
        :param variant: product.product()
        :param instance: magento.instance()
        :return: dictionary
        """
        template = variant.product_tmpl_id
        return {
            'product_template_id': template.id,
            'product_id': variant.id,
            'template_name': template.name,
            'product_name': variant.name,
            'product_default_code': variant.default_code,
            'magento_sku': variant.default_code,
            'description': variant.description or "",
            'sale_description': template.description_sale if template.description_sale else '',
            'instance_id': instance.id
        }

    def prepare_product_for_magento(self, variants):
        """
        Add product and product template into Magento.
        create product dictionary with details.
        :param variants: Odoo product product object
        :return:
        """
        product_dict = dict()
        if self.magento_instance_id:
            product_dict.update({'instance_id': self.magento_instance_id.id})
            for variant in variants:
                product_dict.update({
                    'product_id': variant.id,
                    'magento_sku': variant.default_code,
                    'description': variant.description,
                    'sale_description': variant.description_sale,
                    'product_template_id': variant.product_tmpl_id.id
                })
                self.mapped_magento_products(product_dict)
        return True

    def import_magento_csv(self, instance):
        """
        This method use for Read all data from CSV file
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param instance: Magento instance object
        :return: Missing magento sku which is not set or any errors
        """
        csv_reader = csv.DictReader(StringIO(base64.b64decode(self.datas).decode()), delimiter=',')
        row_no = 1
        for product_dict in csv_reader:
            row_no += 1
            self.mapped_products_validate(product_dict, instance, row_no)
        return True

    def import_magento_xls(self, instance):
        """
        This method use for Read all data from XLS/XLSX file
        Develop by : Hardik Dhankecha
        Date : 22/10/2021
        :param instance: Magento instance object
        :return: Missing magento sku which is not set or any errors
        """
        sheets = xlrd.open_workbook(file_contents=base64.b64decode(self.datas.decode('UTF-8')))
        header = dict()
        is_header = False
        for sheet in sheets.sheets():
            for row_no in range(sheet.nrows):
                if not is_header:
                    headers = [d.value for d in sheet.row(row_no)]
                    [header.update({d: headers.index(d)}) for d in headers]
                    is_header = True
                    continue
                row = dict()
                [row.update({k: sheet.row(row_no)[v].value}) for k, v in header.items() for c in
                 sheet.row(row_no)]
                self.mapped_products_validate(row, instance, row_no)
        return True

    def mapped_products_validate(self, row, instance, row_no):
        """
        This method use for Add product and product template into Magento.
        create product dictionary with details.
        Develop by : Prashant Ramoliya
        Date : 2/Nov/2021
        :param row: dict(product)
        :param instance: Magento instance object
        :param row_no: current row number of the CSV/XLSX file
        :return: Missing magento sku which is not set or any errors
        """
        logs = list()
        row = self._update_row(row)
        log_line = self.validate_product_dict(row, instance, row_no)
        if log_line:
            logs.append(log_line)
            return logs
        self.mapped_magento_products(row)
        return True

    @staticmethod
    def _update_row(row):
        row.update({
            'product_id': int(row.get('product_id') or 0),
            'product_template_id': int(row.get('product_template_id') or 0),
            'instance_id': int(row.get('instance_id') or 0)
        })
        return row

    def validate_product_dict(self, row, instance, row_number):
        """
        This method check columns values is set properly or not.
        skip this not properly values line.
        Develop by : Prashant Ramoliya
        Date : 2/Nov/2021
        :param instance: Magento instance object
        :param row: dict of line from product csv/xls file
        :param row_number: current row number of the CSV/XLSX file
        :return: Missing magento sku which is not set or any errors
        """
        log_line = list()
        if row.get('instance_id') != instance.id:
            message = "Skip the line [{}] because of instance not set properly" \
                      "in the file".format(row_number)
            log_line.append((0, 0, {'message': message}))
            return log_line
        product = self.env['product.product'].browse(row.get('product_id'))
        if not product:
            message = "Skip the line [{}] because of product_id is blank not allowed. " \
                      "in the file".format(row_number)
            log_line.append((0, 0, {'message': message}))
            return log_line
        if not row.get('magento_sku'):
            row.update({'magento_sku': product.default_code or ''})
        if not row.get('magento_sku', False):
            message = "Skip the line [{}] because of magento SKU is blank not allowed. " \
                      "in the file".format(row_number)
            log_line.append((0, 0, {'message': message}))
            return log_line
        template = self.env['product.template'].browse(row.get('product_template_id'))
        if not template:
            message = "Skip the line [{}] because of product_template_id is blank not allowed. " \
                      "in the file".format(row_number)
            log_line.append((0, 0, {'message': message}))
            return log_line
        return log_line

    def mapped_magento_products(self, row):
        """
        Map Odoo products with Magento Products
        :param row: dict of line from product csv file
        :return: dict of missing magento sku
        """
        product = self.env['product.product'].browse(row.get('product_id'))
        self.create_magento_product_variant(row, product)
        # self._cr.commit()
        return True

    def create_magento_product_template(self, row, product):
        """
        Create magento product template when import product using CSV.
        :param row: dict(CSC/XLSX row)
        :param product: dict(product)
        :return: Magento Product Template Object
        """
        m_template = self.env['magento.product.template']
        domain = self.prepare_magento_template_search_domain(row, product)
        m_template = m_template.search(domain)
        if not m_template:
            template = self.env['product.template'].browse(row.get('product_template_id'))
            template_val = self.prepare_magento_template_values_ept(row, template)
            m_template = m_template.create(template_val)
            self.create_magento_template_images(m_template, template)
        return m_template

    @staticmethod
    def prepare_magento_template_search_domain(row, product):
        """
        Prepare Domain for Search Magento Products
        :param row: dict
        :param product: product.product()
        :return: list(tuple())
        """
        if len(product.product_tmpl_id.product_variant_ids) > 1:
            return [('magento_instance_id', '=', row.get('instance_id')),
                    ('odoo_product_template_id', '=', row.get('product_template_id'))]
        else:
            return [('magento_instance_id', '=', row.get('instance_id')),
                    ('magento_sku', '=', row.get('magento_sku'))]

    def prepare_magento_template_values_ept(self, product_dict, template):
        """
        this methods set values of create magento template.
        :param product_dict: dict
        :param template: odoo product template object
        :return : create product values (dict)
        """
        ipc = self.env["ir.config_parameter"].sudo()
        m_values = {
            'magento_instance_id': product_dict.get('instance_id'),
            'odoo_product_template_id': product_dict.get('product_template_id'),
            'product_type': 'configurable' if template.product_variant_count > 1 else 'simple',
            'magento_product_name': template.name,
            'magento_sku': template.product_variant_count == 1 and product_dict.get('magento_sku'),
            'export_product_to_all_website': True
        }
        if ipc.get_param("odoo_magento2_ept.set_magento_sales_description"):
            m_values.update({
                'description': product_dict.get('description', ''),
                'short_description': product_dict.get('sale_description', ''),
            })
        return m_values

    def create_magento_product_variant(self, row, product):
        """
        Create or update Magento Product Variant when import product using CSV.
        :param row: dict {}
        :param product: product.product()
        :return:
        """
        m_product = self.env[MAGENTO_PRODUCT_PRODUCT]
        domain = self.prepare_magento_product_search_domain(row)
        m_variant = m_product.search(domain)
        if not m_variant:
            # We are creating magento.template
            m_template = self.create_magento_product_template(row, product)
            # We are creating magento.product
            prod_values = self.prepare_magento_product_values_ept(row, product, m_template)
            m_product = m_product.create(prod_values)
            self.create_magento_product_images(m_template, product, m_product)
        return True

    @staticmethod
    def prepare_magento_product_search_domain(row):
        """
        Prepare Domain for Search Magento Products
        :param row: dict
        :return: list(tuple())
        """
        return [('magento_instance_id', '=', row.get('instance_id')),
                ('magento_sku', '=', row.get('magento_sku'))]

    def prepare_magento_product_values_ept(self, product_dict, product, m_template):
        """
        this methods set values of create magento product.
        :param product_dict: dict
        :param product: odoo product object
        :param m_template: magento product template.
        :return : create product values (dict)
        """
        ir_config = self.env["ir.config_parameter"].sudo()
        m_values = {
            'magento_instance_id': product_dict.get('instance_id'),
            'odoo_product_id': product.id,
            'magento_tmpl_id': m_template.id,
            'magento_sku': product_dict.get('magento_sku'),
            'magento_product_name': product.name
        }
        if ir_config.get_param("odoo_magento2_ept.set_magento_sales_description"):
            m_values.update({
                'description': product_dict.get('description', ''),
                'short_description': product_dict.get('sale_description', ''),
            })
        return m_values

    def download_sample_attachment(self):
        """
        This Method relocates download sample file of internal transfer.
        :return: This Method return file download file.
        """
        attachment = self.env['ir.attachment'].search([('name', '=', 'magento_product_export.csv')])
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    def create_magento_template_images(self, m_template, template):
        """
        This method is use to create images in Magento layer.
        :param m_template: magento product template object
        :param template: product template object
        """
        m_image = self.env["magento.product.image"]
        m_image_list = []
        sequence = 1
        for image in template.ept_image_ids.filtered(lambda x: not x.product_id):
            if template.image_1920 and image.image == template.image_1920:
                sequence = 0
            magento_image = m_image.search([("magento_tmpl_id", "=", m_template.id),
                                            ("odoo_image_id", "=", image.id)])
            if not magento_image:
                m_image_list.append({
                    "odoo_image_id": image.id,
                    "magento_tmpl_id": m_template.id,
                    'url': image.url,
                    'image': image.image,
                    'magento_instance_id': m_template.magento_instance_id.id,
                    'sequence': sequence
                })
            sequence += 1
        if m_image_list:
            m_image.create(m_image_list)
        return True

    def create_magento_product_images(self, m_template, product, m_product):
        """
        This method is use to create images in Magento layer.
        :param m_template: magneto product template object
        :param product: product  object
        :param m_product: magento product object
        """
        m_image = self.env["magento.product.image"]
        m_image_list = []
        sequence = 1
        for image in product.ept_image_ids:
            if product.image_1920 and image.image == product.image_1920:
                sequence = 0
            magento_image = m_image.search([("magento_tmpl_id", "=", m_template.id),
                                            ("magento_product_id", "=", m_product.id),
                                            ("odoo_image_id", "=", image.id)])
            if not magento_image:
                m_image_list.append({
                    "odoo_image_id": image.id,
                    "magento_tmpl_id": m_template.id,
                    "magento_product_id": m_product.id if m_product else False,
                    'url': image.url,
                    'image': image.image,
                    'magento_instance_id': m_template.magento_instance_id.id,
                    'sequence': sequence
                })
            sequence += 1
        if m_image_list:
            m_image.create(m_image_list)
        return True
