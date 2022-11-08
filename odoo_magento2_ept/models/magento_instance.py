# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for Magento Instance
"""
import json
import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import ustr
from .api_request import req

_secondsConverter = {
    'days': lambda interval: interval * 24 * 60 * 60,
    'hours': lambda interval: interval * 60 * 60,
    'weeks': lambda interval: interval * 7 * 24 * 60 * 60,
    'minutes': lambda interval: interval * 60,
}
_logger = logging.getLogger('MagentoInstance')


class MagentoInstance(models.Model):
    """
    Describes methods for Magento Instance
    """
    _name = 'magento.instance'
    _description = 'Magento Instance'

    @api.model
    def _default_set_import_product_category(self):
        return self.env.ref('product.product_category_all').id \
            if self.env.ref('product.product_category_all') else False

    @api.model
    def _default_magento_discount_product(self):
        """
        This method is used to set the discount product in an instance.
        @author: Hardik Dhankecha on Date 28-Sep-2021.
        """
        discount_product = self.env.ref('odoo_magento2_ept.magento_product_product_discount', False)
        if not discount_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n"
                              "Maybe the Discount product has been deleted, it will be "
                              "recreated at the time of module upgrade."))
        return discount_product

    @api.model
    def _default_magento_shipping_product(self):
        """
        This method is used to set the shipping product in an instance.
        @author: Hardik Dhankecha on Date 28-Sep-2021.
        """
        shipping_product = self.env.ref('odoo_magento2_ept.product_product_shipping', False)
        if not shipping_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n"
                              "Maybe the shipping product has been deleted, it will be "
                              "recreated at the time of module upgrade."))
        return shipping_product

    @api.model
    def _default_order_status(self):
        """
        Get default status for importing magento order.
        :return:
        """
        order_status = self.env.ref('odoo_magento2_ept.pending')
        return [(6, 0, [order_status.id])] if order_status else False

    @api.model
    def set_magento_import_after_date(self):
        """ It is used to set after order date which has already created an instance.
        """
        sale_order_obj = self.env["sale.order"]
        instances = self.search([])
        order_after_date = datetime.now() - timedelta(30)
        for instance in instances:
            if not instance.import_order_after_date:
                order = sale_order_obj.search([('magento_instance_id', '=', instance.id)],
                                              order='date_order asc', limit=1) or False
                if order:
                    order_after_date = order.date_order
                else:
                    order_after_date = datetime.now() - timedelta(30)
                instance.write({"import_order_after_date": order_after_date})
        return order_after_date

    name = fields.Char(string="Instance Name", required=True)
    magento_version = fields.Selection([('2.1', '2.1.*'), ('2.2', '2.2.*'), ('2.3', '2.3.*')],
                                       string="Magento Versions", required=True,
                                       help="Version of Magento Instance")
    magento_url = fields.Char(string='Magento URLs', required=False, help="URL of Magento")
    magento_admin_url = fields.Char(string='Magento Admin URL', required=False, help="URL of Magento Backend")
    warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', string="Warehouses",
                                     required=True,
                                     help='Warehouses used to compute the stock quantities.'
                                          'If Warehouses is not selected then it is taken from '
                                          'Website')
    magento_website_ids = fields.One2many(comodel_name='magento.website',
                                          inverse_name='magento_instance_id',
                                          string='Website', readonly=True, help="Magento Websites")
    lang_id = fields.Many2one(comodel_name='res.lang', string='Default Language',
                              help="If a default language is selected, records will be imported in "
                                   "the translation of this language.\n"
                                   "Note that a similar configuration exists for each storeview.")
    magento_stock_field = fields.Selection([('onhand_qty', 'On Hand Quantity'),
                                            ('free_qty', 'On Hand Quantity'),
                                            ('virtual_available', 'Forcast Quantity')],
                                           string="Magento Stock Type", default='free_qty',
                                           help="Magento Stock Type")
    catalog_price_scope = fields.Selection([('global', 'Global'), ('website', 'Website')],
                                           string="Catalog Price Scopes",
                                           help="Scope of Price in Magento", default='global')
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string="Pricelist",
                                   help="Product Price is set in selected Pricelist")
    cost_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string="Cost Pricelist",
                                        help="Product Cost Price is set in selected Pricelist")
    access_token = fields.Char(string="Magento Access Token", help="Magento Access Token")
    auto_create_product = fields.Boolean(string="Auto Create Magento Product", default=False,
                                         help="Checked True, if you want to create new product in "
                                              "Odoo if not found. \nIf not checked, Job will be "
                                              "failed while import order or product.")
    allow_import_image_of_products = fields.Boolean(comodel_name="Import Images of Products",
                                                    default=False,
                                                    help="Import product images along with product "
                                                         "from Magento while import product?")
    last_product_import_date = fields.Datetime(string='Last Import Products date',
                                               help="Last Import Products date")
    last_order_import_date = fields.Datetime(string="Last Shipped Orders import date",
                                             help="Last Shipped Orders import date")

    last_unshipped_order_import_date = fields.Datetime(string="Last Unshipped Orders import date",
                                             help="Last Unshipped Orders import date")

    last_cancel_order_import_date = fields.Datetime(string="Last Cancel Orders import date",
                                             help="Last Cancel Orders import date")

    last_update_stock_time = fields.Datetime(string="Last Update Product Stock Time",
                                             help="Last Update Stock Time")

    # Import Product Stock
    is_import_product_stock = fields.Boolean(string='Is Import Magento Product Stock?',
                                             default=False,
                                             help="Import Product Stock from Magento to Odoo")
    import_stock_warehouse = fields.Many2one(comodel_name='stock.warehouse',
                                             string="Import Product Stock Warehouse",
                                             help="Warehouse for import stock from Magento to Odoo")
    active = fields.Boolean(string="Status", default=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Magento Company',
                                 help="Magento Company")
    invoice_done_notify_customer = fields.Boolean(string="Invoices Done Notify customer",
                                                  default=False,
                                                  help="while export invoice send email")
    is_multi_warehouse_in_magento = fields.Boolean(string="Is Multi Warehouse in Magento?",
                                                   default=False,
                                                   help="If checked, Multi Warehouse used in "
                                                        "Magento")
    # Require filed for cron
    auto_import_sale_orders = fields.Boolean(string="Auto Import Shipped Sale Orders?", default=False,
                                             help="This Field relocate auto import shipped sale orders.")

    auto_import_unshipped_sale_orders = fields.Boolean(string="Auto Import Unshipped Sale Orders?", default=False,
                                             help="This Field relocate auto import unshipped sale orders.")

    auto_import_cancel_sale_orders = fields.Boolean(string="Auto Import Cancel Sale Orders?", default=False,
                                             help="This Field relocate auto import sale orders.")
    auto_import_product = fields.Boolean(string='Auto import product?',
                                         help="Auto Automatic Import Product")
    auto_export_product_stock = fields.Boolean(string='Auto Export Product Stock?',
                                               help="Automatic Export Product Stock")
    auto_export_invoice = fields.Boolean(string='Auto Export Invoice?',
                                         help="Auto Automatic Export Invoice")
    auto_export_shipment_order_status = fields.Boolean(string='Auto Export Shipment Information?',
                                                       help="Automatic Export Shipment Information")
    payment_method_ids = fields.One2many(comodel_name="magento.payment.method",
                                         inverse_name="magento_instance_id",
                                         help="Payment Methods for Magento")
    shipping_method_ids = fields.One2many(comodel_name="magento.delivery.carrier",
                                          inverse_name="magento_instance_id",
                                          help="Shipping Methods for Magento")
    import_magento_order_status_ids = fields.Many2many('import.magento.order.status',
                                                       'magento_instance_order_status_rel',
                                                       'magento_instance_id', 'order_status_id',
                                                       string="Import Order Status",
                                                       default=_default_order_status,
                                                       help="Select order status in which you want "
                                                            "to import the orders from Magento to "
                                                            "Odoo.")
    active = fields.Boolean(string="Status", default=True)
    magento_import_customer_current_page = fields.Integer(string="Magento Import Customer Current "
                                                                 "Pages", default=1,
                                                          help="It will fetch customers from "
                                                               "Magento of given page.")
    magento_import_order_page_count = fields.Integer(string="Magento Import order Page Count",
                                                     default=1,
                                                     help="It will fetch order of Magento from "
                                                          "given page numbers.")
    magento_import_product_page_count = fields.Integer(string="Magento Import Products Page Count",
                                                       default=1,
                                                       help="It will fetch products of Magento "
                                                            "from given page numbers.")
    import_product_category = fields.Many2one(comodel_name='product.category',
                                              string="Import Product Categories",
                                              default=_default_set_import_product_category,
                                              help="While importing a product, the selected "
                                                   "category will set in that product.")
    discount_product_id = fields.Many2one(comodel_name="product.product", string="Discount Product",
                                          domain=[('type', '=', 'service')],
                                          default=_default_magento_discount_product,
                                          help="This is used for set discount product in a sale "
                                               "order lines")
    shipping_product_id = fields.Many2one(comodel_name="product.product", string="Shipping Product",
                                          domain=[('type', '=', 'service')],
                                          default=_default_magento_shipping_product,
                                          help="This is used for set shipping product in a Carrier")
    is_instance_create_from_onboarding_panel = fields.Boolean(default=False)
    is_onboarding_configurations_done = fields.Boolean(default=False)
    import_order_after_date = fields.Datetime(help="Connector only imports those orders which"
                                                   " have created after a "
                                                   "given date.",
                                              default=set_magento_import_after_date)
    magento_verify_ssl = fields.Boolean(string="Verify SSL", default=False,
                                        help="Check this if your Magento site is using SSL "
                                             "certificate")
    active_user_ids = fields.One2many(comodel_name="magento.api.request.page",
                                      inverse_name="magento_instance_id", string='Active Users',
                                      help='Active Users')
    magento_apply_tax_in_order = fields.Selection([
        ("odoo_tax", "Odoo Default Tax Behaviour"),
        ("create_magento_tax", "Create New Tax If Not Found")], copy=False,
        default="create_magento_tax",
        help=""" For Magento Orders :- \n
            1) Odoo Default Tax Behaviour - The Taxes will be set based on Odoo's default functional 
            behaviour i.e. based on Odoo's Tax and Fiscal Position configurations. \n
            2) Create New Tax If Not Found - System will search the tax data received 
            from Magento in Odoo, will create a new one if it fails in finding it.""")

    magento_invoice_tax_account_id = fields.Many2one(comodel_name="account.account",
                                                     string="Invoice Tax Account For Magento Tax")
    magento_credit_tax_account_id = fields.Many2one(comodel_name="account.account",
                                                    string="Credit Note Tax Account For Magento Tax")
    magento_tax_rounding_method = fields.Selection([("round_per_line", "Round per Line"),
                                                    ("round_globally", "Round Globally")],
                                                   default="round_per_line")

    # Schedule Activity Fields
    activity_type = fields.Many2one(comodel_name="mail.activity.type",
                                    string="Activity Type")
    is_create_activity = fields.Boolean(string="Is Create Schedule Activity?")
    activity_user_ids = fields.Many2many(comodel_name='res.users',
                                         string="Activity User",
                                         help="Schedule activity will be create against this user.")
    activity_lead_days = fields.Integer(string="Lead Days",
                                        help="Activity will be created after this days.")
    # Export Product
    batch_size = fields.Integer(string="Export Stock Batch Size", default=200,
                                help="Export product batch size.")
    magento_analytic_account_id = fields.Many2one('account.analytic.account',
                                                  string='Analytic Account')
    magento_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    is_magento_digest = fields.Boolean(string="Set Magento Digest?")
    is_order_base_currency = fields.Boolean(
        string="Import Order with base currency",
        default=False,
        help="Import Order with base currency check"
    )

    _sql_constraints = [('unique_magento_host', 'unique(magento_url, access_token)',
                         "Instance already exists for given host. Host or Access Token must be Unique for the instance!")]

    @api.onchange('batch_size')
    def _onchange_batch_size(self):
        if self.batch_size < 0 or self.batch_size > 300:
            raise UserError("Export stock batch size will only allow the 0-300 batch size value.")

    def check_dashboard_view(self):
        """
        It will display dashboard based on configuration either by instance wise or website wise.
        :return:
        """
        view_type = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_magento2_ept.dashboard_view_type")
        if view_type == 'instance_level':
            instance_action = 'odoo_magento2_ept.action_magento_dashboard_instance'
            view = self.env.ref(instance_action).sudo().read()[0]
        else:
            website_action = 'odoo_magento2_ept.action_magento_dashboard_website'
            view = self.env.ref(website_action).sudo().read()[0]
        action = self.prepare_action(view, [])
        return action

    def _compute_get_scheduler_list(self):
        seller_cron = self.env['ir.cron'].sudo().search([('magento_instance_id', '=', self.id)])
        for record in self:
            record.cron_count = len(seller_cron.ids)

    cron_count = fields.Integer(string="Scheduler Count",
                                compute="_compute_get_scheduler_list",
                                help="This Field relocates Scheduler Count.")

    def list_of_delivery_method(self):
        """
        This method is for list all delivery method
        Task : 173954 - Add delivery method new screen
        Develop by Hardik Dhankecha
        :return:
        """
        tree_view = self.env.ref('odoo_magento2_ept.magento_delivery_carrier_tree_view').id
        action = {
            'name': 'Magento Carriers Views',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.delivery.carrier',
            'views': [(tree_view, 'tree')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [("magento_instance_id", "=", self.id)]
        }
        return action

    def list_of_instance_cron(self):
        """
        Opens view for cron scheduler of instance
        :return:
        """
        instance_cron = self.env['ir.cron'].search([('magento_instance_id', '=', self.id)])
        action = {
            'domain': "[('id', 'in', " + str(instance_cron.ids) + " )]",
            'name': 'Cron Scheduler',
            'view_mode': 'tree,form',
            'res_model': 'ir.cron',
            'type': 'ir.actions.act_window',
        }
        return action

    def get_magento_cron_execution_time(self, cron_name):
        """
        This method is used to get the interval time of the cron.
        @param cron_name: External ID of the Cron.
        @return: Interval time in seconds.
        @author: Maulik Barad on Date 25-Nov-2020.
        """
        process_queue_cron = self.env.ref(cron_name, False)
        if not process_queue_cron:
            raise UserError(
                _("Please upgrade the module. \n Maybe the job has been deleted, it will be recreated at "
                  "the time of module upgrade."))
        interval = process_queue_cron.interval_number
        interval_type = process_queue_cron.interval_type
        if interval_type == "months":
            days = 0
            current_year = fields.Date.today().year
            current_month = fields.Date.today().month
            for i in range(0, interval):
                month = current_month + i

                if month > 12:
                    if month == 13:
                        current_year += 1
                    month -= 12

                days_in_month = monthrange(current_year, month)[1]
                days += days_in_month

            interval_type = "days"
            interval = days
        interval_in_seconds = _secondsConverter[interval_type](interval)
        return interval_in_seconds

    def toggle_active(self):
        """
        This method is overridden for archiving other properties, while archiving the instance from the Action menu.
        """
        context = dict(self._context)
        context.update({'active_ids': self.ids})
        action = self[0].with_context(
            context).magento_action_open_deactive_wizard() if self else False
        return action

    def magento_action_open_deactive_wizard(self):
        """
        This method is used to open a wizard to display the information related to how many data active/inactive
        while instance Active/Inactive.
        :return: action
        """
        view = self.env.ref('odoo_magento2_ept.view_inactive_magento_instance')
        return {
            'name': _('Instance Active/Inactive Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'magento.queue.process.ept',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self._context,
        }

    def magento_action_archive_unarchive(self):
        """
        This method archive/active related website, storeviews, products, queues,
        financial status, inventory locations when instance archive/ active.
        :return:
        """
        domain = [("magento_instance_id", "=", self.id)]
        magento_template_obj = self.env["magento.product.template"]
        magento_financial_status_obj = self.env["magento.financial.status.ept"]
        magento_payment_method_obj = self.env["magento.payment.method"]
        magento_inventory_location_obj = self.env["magento.inventory.locations"]
        magento_website_obj = self.env['magento.website']
        magento_storeview_obj = self.env['magento.storeview']
        data_queue_mixin_obj = self.env['data.queue.mixin.ept']
        ir_cron_obj = self.env["ir.cron"]
        if self.active:
            activate = {"active": False}
            auto_crons = ir_cron_obj.search([("name", "ilike", self.name), ("active", "=", True)])
            if auto_crons:
                auto_crons.write(activate)
            data_queue_mixin_obj.delete_data_queue_ept(is_delete_queue=True)
            magento_website_obj.search(domain).write(activate)
            magento_storeview_obj.search(domain).write(activate)
            magento_inventory_location_obj.search(domain).write(activate)
            magento_financial_status_obj.search(domain).write(activate)
            magento_payment_method_obj.search(domain).write(activate)
            company = self.company_id
            company.write({
                'magento_instance_onboarding_state': 'not_done',
                'magento_basic_configuration_onboarding_state': 'not_done',
                'magento_financial_status_onboarding_state': 'not_done',
                'magento_cron_configuration_onboarding_state': 'not_done',
                'is_create_magento_more_instance': False
            })
            magento_order_counts = self.active_user_ids
            for magento_order_count in magento_order_counts:
                magento_order_count.write({'magento_import_order_page_count': 1})
            self.write({'is_onboarding_configurations_done': True})
        else:
            activate = {"active": True}
            domain.append(("active", "=", False))
            magento_website_obj.search(domain).write(activate)
            magento_storeview_obj.search(domain).write(activate)
            magento_inventory_location_obj.search(domain).write(activate)
            magento_financial_status_obj.search(domain).write(activate)
            magento_payment_method_obj.search(domain).write(activate)
            self.synchronize_metadata()
        self.write(activate)
        magento_template_obj.search(domain).write(activate)

        return True

    def unlink(self):
        """
        Unlink onboarding panel flags when instance is unlink.
        :return:
        """
        company = self.company_id
        company.write({
            'magento_instance_onboarding_state': 'not_done',
            'magento_basic_configuration_onboarding_state': 'not_done',
            'magento_financial_status_onboarding_state': 'not_done',
            'magento_cron_configuration_onboarding_state': 'not_done',
            'is_create_magento_more_instance': False
        })
        self.write({'is_onboarding_configurations_done': True})
        res = super(MagentoInstance, self).unlink()
        return res

    def cron_configuration_action(self):
        """
        Return action for cron configuration
        :return:
        """
        action = self.env.ref(
            'odoo_magento2_ept.action_magento_wizard_cron_configuration_ept'
        ).read()[0]
        context = {
            'magento_instance_id': self.id
        }
        action['context'] = context
        return action

    def magento_test_connection(self):
        """
        This method check connection in magento.
        """
        self.ensure_one()
        try:
            api_url = "/V1/store/websites"
            website_response = req(self, api_url, method='GET')
        except Exception as error:
            raise UserError(
                _("Connection Test Failed! Here is what we got instead:\n \n%s") % ustr(error))
        if website_response:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': "Connection Test Succeeded! Everything seems properly set up!",
                    'img_url': '/web/static/src/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }

    def synchronize_metadata(self):
        """
        Sync all the websites, store view , Payment methods and delivery methods
        """
        for record in self:
            record.sync_price_scop()
            record.import_currency()
            record.sync_website()
            record.sync_storeview()
            record.import_payment_method()
            record.import_delivery_method()
            record.import_magento_inventory_locations()
            self.env['magento.order.status.ept'].create_order_status(record)
            self.env['magento.financial.status.ept'].create_financial_status(record, 'not_paid')
            self.env['magento.api.request.page'].update_magento_order_page_count_users_vise(record)

    def sync_price_scop(self):
        """
        get price attribute scope and set it in the current instance.
        :return:
        """
        api_url = "/V1/products/attributes/price"
        try:
            attributes_price = req(self, api_url, method='GET')
        except Exception as error:
            raise UserError(error)

        self.catalog_price_scope = attributes_price.get('scope')

    def sync_website(self):
        """
        Sync all the websites from magento
        """
        try:
            website_response = req(self, "/V1/store/websites", method='GET')
        except Exception as error:
            raise UserError(error)
        for data in website_response:
            magento_website_id = data.get('id')
            if magento_website_id != 0:
                mage_website_id = self.search_magento_website_id(str(magento_website_id))
                if not mage_website_id:
                    self.env['magento.website'].create({
                        'name': data.get('name'),
                        'magento_website_id': magento_website_id,
                        'magento_instance_id': self.id,
                        'warehouse_id': self.warehouse_ids.id
                    })

    def search_magento_website_id(self, magento_website_id):
        return self.magento_website_ids.filtered(
            lambda x: x.magento_website_id == str(
                magento_website_id) and x.magento_instance_id.id == self.id)

    def open_all_websites(self):
        """
        This method used for smart button for view all website.
        return : Action.
        """
        form_view_id = self.env.ref('odoo_magento2_ept.view_magento_website_form').id
        tree_view = self.env.ref('odoo_magento2_ept.view_magento_website_tree').id
        action = {
            'name': 'Magento Website',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'magento.website',
            'views': [(tree_view, 'tree'), (form_view_id, 'form')],
            'view_id': tree_view,
            'target': 'current',
            'domain': [('id', 'in', self.magento_website_ids.ids)]
        }
        return action

    def sync_storeview(self):
        """
        This method used for import all storeview from magento.
        """
        storeview_obj = self.env['magento.storeview']
        response = req(self, "/V1/store/storeConfigs", method='GET')
        stores = req(self, "/V1/store/storeViews", method='GET')
        for storeview_data in response:
            magento_storeview_id = storeview_data.get('id')
            if magento_storeview_id != 0:
                storeview = storeview_obj.search([
                    ('magento_storeview_id', '=', magento_storeview_id),
                    ('magento_instance_id', '=', self.id)
                ])
                odoo_website_id = self.update_pricelist_in_website(storeview_data)
                if not storeview:
                    name, language = self.get_store_view_language_and_name(stores,
                                                                           magento_storeview_id,
                                                                           storeview_data)
                    storeview_obj.create({
                        'name': name,
                        'magento_website_id': odoo_website_id.id,
                        'magento_storeview_id': magento_storeview_id,
                        'magento_instance_id': self.id,
                        'base_media_url': storeview_data.get('base_media_url'),
                        'lang_id': language.id,
                        'magento_storeview_code': storeview_data.get('code')
                    })
                else:
                    storeview.write({
                        'base_media_url': storeview_data.get('base_media_url'),
                        'magento_storeview_code': storeview_data.get('code')
                    })

    def get_store_view_language_and_name(self, stores, magento_storeview_id, storeview_data):
        """
        Get Store view language and name.
        :param stores: Magento stores received from API
        :param magento_storeview_id: Magento store view id
        :param storeview_data: data received from Magento
        :return: name and res language object
        """
        res_lang_obj = self.env['res.lang']
        name = ''
        for store in stores:
            if store['id'] == magento_storeview_id:
                name = store['name']
                break
        lang = storeview_data.get('locale')
        if lang:
            language = res_lang_obj.with_context(active_test=False).search([('code', '=', lang)])
            if language and not language.active:
                language.write({'active': True})
        return name, language

    def update_pricelist_in_website(self, storeview_data):
        """
        If Website is found, then update price list based on store currency.
        :param storeview_data: Store view response received from Magento.
        :return: Magento website object
        """
        website_obj = self.env['magento.website']
        pricelist_obj = self.env['product.pricelist']
        currency_obj = self.env['res.currency']
        odoo_website_id = website_obj.search([
            ('magento_website_id', '=', storeview_data.get('website_id')),
            ('magento_instance_id', '=', self.id)
        ], limit=1)
        if odoo_website_id:
            currency_id = currency_obj.with_context(active_test=False).search([
                ('name', '=', storeview_data.get('base_currency_code'))], limit=1)
            if currency_id and not currency_id.active:
                currency_id.write({'active': True})
            elif not currency_id:
                currency_id = self.env.user.currency_id
            price_list_name = self.name + ' ' + 'PriceList - ' + odoo_website_id.name
            pricelist_id = pricelist_obj.search([
                ('name', '=', price_list_name), ('currency_id', '=', currency_id.id)
            ], limit=1)
            if not pricelist_id:
                pricelist_id = pricelist_obj.create(
                    {'name': price_list_name, 'currency_id': currency_id.id})

            base_pricelist_name = self.name + ' ' + 'Cost PriceList - ' + odoo_website_id.name
            base_pricelist_id = pricelist_obj.search([
                ('name', '=', base_pricelist_name), ('currency_id', '=', currency_id.id)
            ], limit=1)
            if not base_pricelist_id:
                base_pricelist_id = pricelist_obj.create({'name': base_pricelist_name, 'currency_id': currency_id.id})
            odoo_website_id.write({
                'magento_base_currency': currency_id,
                'pricelist_ids': [(6, 0, [pricelist_id.id])],
                'cost_pricelist_id': base_pricelist_id.id
            })
        return odoo_website_id

    def import_payment_method(self):
        """
        This method used for import payment method.
        """
        payment_method_obj = self.env['magento.payment.method']
        url = '/V1/paymentmethod'
        payment_methods = req(self, url)
        for payment_method in payment_methods:
            payment_method_code = payment_method.get('value')
            new_payment_method = payment_method_obj.search([
                ('payment_method_code', '=', payment_method_code),
                ('magento_instance_id', '=', self.id)
            ])
            if not new_payment_method:
                name = f"{payment_method.get('title')} ({payment_method.get('value')})"
                payment_method_obj.create({
                    'payment_method_code': payment_method.get('value'),
                    'payment_method_name': name,
                    'magento_instance_id': self.id
                })

    def import_delivery_method(self):
        """
        This method used for import delivery method.
        """
        delivery_method_obj = self.env['magento.delivery.carrier']
        url = '/V1/shippingmethod'
        delivery_methods = req(self, url)
        for delivery_method in delivery_methods:
            for method_value in delivery_method.get('value'):
                delivery_method_code = method_value.get('value')
                new_delivery_carrier = delivery_method_obj.search([
                    ('carrier_code', '=', delivery_method_code),
                    ('magento_instance_id', '=', self.id)
                ])
                if not new_delivery_carrier:
                    delivery_method_obj.create({
                        'carrier_code': method_value.get('value'),
                        'carrier_label': method_value.get('label'),
                        'magento_instance_id': self.id,
                        'magento_carrier_title': delivery_method.get('label')
                    })

    def import_magento_inventory_locations(self):
        """
        This method is used to import Magento Multi inventory sources
        :return:
        """
        if self.is_multi_warehouse_in_magento:
            magento_inventory_location_obj = self.env['magento.inventory.locations']
            try:
                api_url = '/V1/inventory/sources'
                response = req(self, api_url)
            except Exception as error:
                raise UserError(_("Error while requesting inventory locations" + str(error)))
            if response.get('items'):
                for inventory_location in response.get('items'):
                    location_code = inventory_location.get('source_code')
                    magento_location = magento_inventory_location_obj.search([
                        ('magento_location_code', '=', location_code),
                        ('magento_instance_id', '=', self.id)
                    ])
                    if not magento_location:
                        magento_inventory_location_obj.create({
                            'name': inventory_location.get('name'),
                            'magento_location_code': inventory_location.get('source_code'),
                            'active': inventory_location.get('enabled'),
                            'magento_instance_id': self.id
                        })
                    else:
                        magento_location.write({'active': inventory_location.get('enabled')})

    @api.model
    def import_currency(self):
        """
        This method is used to import all currency as pricelist
        :return:
        """
        url = '/V1/directory/currency'
        magento_currency = req(self, url)
        currency_obj = self.env['res.currency']
        magento_base_currency = magento_currency.get('base_currency_code')
        pricelist_obj = self.env['product.pricelist']
        for active_currency in magento_currency.get('exchange_rates'):
            currency_id = currency_obj.with_context(active_test=False). \
                search([('name', '=', active_currency.get('currency_to'))], limit=1)
            if not currency_id.active:
                currency_id.write({'active': True})
            price_list = pricelist_obj.search([('currency_id', '=', currency_id.id)])
            if price_list:
                price_list = price_list[0]
            elif not price_list or price_list.currency_id != currency_id:
                price_list = pricelist_obj.create({
                    'name': self.name + " Pricelist - " + active_currency.get('currency_to'),
                    'currency_id': currency_id.id,
                    'discount_policy': 'with_discount',
                    'company_id': self.company_id.id,
                })
            if magento_base_currency == active_currency.get(
                    'currency_to') and not self.pricelist_id:
                self.write({'pricelist_id': price_list.id})
        return magento_base_currency

    @api.model
    def _scheduler_import_shipped_sale_orders(self, args=None):
        """
        This method is used to import sale order from Magento via cron job.
        :param args: arguments to import complete sale orders
        :return:
        """
        if args is None:
            args = {}
        magento_order_data_queue_obj = self.env['magento.order.data.queue.ept']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            last_order_import_date = instance.last_order_import_date
            if not last_order_import_date:
                last_order_import_date = ''
            from_date = last_order_import_date
            to_date = datetime.now()
            magento_order_data_queue_obj.create_order_queues(
                instance=instance,
                from_date=from_date,
                to_date=to_date,
                status='complete',
            )
            instance.last_order_import_date = datetime.now()

    @api.model
    def _scheduler_import_unshipped_sale_orders(self, args=None):
        """
        This method is used to import sale order from Magento via cron job.
        :param args: arguments to import pending and processing sale orders
        :return:
        """
        if args is None:
            args = {}
        magento_order_data_queue_obj = self.env['magento.order.data.queue.ept']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            order_status = instance.import_magento_order_status_ids.mapped('status')
            last_unshipped_order_import_date = instance.last_unshipped_order_import_date
            if not last_unshipped_order_import_date:
                last_unshipped_order_import_date = ''
            from_date = last_unshipped_order_import_date
            to_date = datetime.now()
            magento_order_data_queue_obj.create_order_queues(
                instance=instance,
                from_date=from_date,
                to_date=to_date,
                status=order_status,
            )
            instance.last_unshipped_order_import_date = datetime.now()

    @api.model
    def _scheduler_import_cancel_sale_orders(self, args=None):
        """
        This method is used to import sale order from Magento via cron job.
        :param args: arguments to import sale orders
        :return:
        """
        if args is None:
            args = {}
        sale_order = self.env['sale.order']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            last_cancel_order_import_date = instance.last_cancel_order_import_date
            if not last_cancel_order_import_date:
                last_cancel_order_import_date = ''
            from_date = last_cancel_order_import_date
            to_date = datetime.now()
            sale_order.import_cancel_order(
                instance=instance,
                from_date=from_date,
                to_date=to_date,
                status='canceled'
            )
            instance.last_cancel_order_import_date = datetime.now()

    @api.model
    def _scheduler_import_product(self, args=None):
        """
        This method is used to import product from Magento via cron job.
        :param args: arguments to import products
        :return:
        """
        if not args:
            return True
        product_queue = self.env['sync.import.magento.product.queue']
        instance = self.env['magento.instance']
        instance_id = args.get('magento_instance_id')
        is_update = args.get('update_existing_product', False)
        if instance_id:
            instance = instance.browse(instance_id)
            from_date = ''
            if instance.last_product_import_date:
                from_date = instance.last_product_import_date
            to_date = datetime.now()
            p_types = ['configurable', 'simple']
            for p_type in p_types:
                product_queue.create_product_queues(instance, from_date, to_date, p_type, is_update)
            instance.write({
                'last_product_import_date': datetime.now()
            })
        return True

    @api.model
    def _scheduler_update_product_stock_qty(self, args=None):
        """
        This method is used to export product stock quantity to Magento via cron job.
        :param args: arguments to export product stock quantity.
        :return:
        """
        if args is None:
            args = {}
        instance = self.env['magento.instance']
        instance_ids = args.get('magento_instance_id')
        export = self.env['magento.export.product.ept']
        if instance_ids:
            instances = instance.browse(instance_ids)
            export.export_product_stock_operation(instances)
        return True

    @api.model
    def _scheduler_update_order_status(self, args=None):
        """
        This method is used to export shipment to Magento via cron job.
        :param args: arguments to export invoice
        :return:
        """
        if args is None:
            args = {}
        picking = self.env['stock.picking']
        m_instance = self.env["magento.instance"]
        if args.get('magento_instance_id', 0):
            instance = m_instance.browse(args.get('magento_instance_id'))
            if instance:
                pickings = picking.search_magento_pickings(instance=instance)
                pickings.with_context(auto_export=True).magento_send_shipment(raise_error=False)
        return True

    @api.model
    def _scheduler_export_invoice(self, args=None):
        """
        This method is used to export invoices to Magento via cron job.
        :param args: arguments to export invoice
        :return:
        """
        if args is None:
            args = {}
        account_move = self.env['account.move']
        magento_instance = self.env['magento.instance']
        magento_instance_id = args.get('magento_instance_id')
        if magento_instance_id:
            instance = magento_instance.browse(magento_instance_id)
            account_move.export_invoices_to_magento(instance)

    def write(self, vals):
        """
        Remove '/' from the magento URL if exist
        :param vals:
        :return:
        """
        if 'magento_url' in vals:
            vals['magento_url'] = vals['magento_url'].rstrip('/')
        res = super(MagentoInstance, self).write(vals)
        return res

    def search_magento_instance(self):
        """
        Search Magento Instance for on-boarding panel.
        :return: magento.instance object
        """
        company = self.env.company or self.env.user.company_id
        instance = self.search([('is_instance_create_from_onboarding_panel', '=', True),
                                ('is_onboarding_configurations_done', '=', False),
                                ('company_id', '=', company.id)], limit=1, order='id desc')
        if not instance:
            instance = self.search([('company_id', '=', company.id),
                                    ('is_onboarding_configurations_done', '=', False)],
                                   limit=1, order='id desc')
            instance.write({'is_instance_create_from_onboarding_panel': True})
        return instance

    # Add new dashboard view

    active = fields.Boolean(string="Status", default=True)
    color = fields.Integer(string='Color Index')
    magento_order_data = fields.Text(compute="_compute_kanban_magento_order_data")
    website_display_currency = fields.Many2one("res.currency",
                                               readonly=True,
                                               help="Display currency of the magento website.")

    def _compute_kanban_magento_order_data(self):
        if not self._context.get('sort'):
            context = dict(self.env.context)
            context.update({'sort': 'week'})
            self.env.context = context
        for record in self:
            # Prepare values for Graph
            values = record.get_graph_data(record)
            data_type, comparison_value = record.get_compare_data(record)
            # Total sales
            total_sales = round(sum([key['y'] for key in values]), 2)
            # Product count query
            exported = 'All'
            product_data = record.get_total_products(record, exported)
            # Customer count query
            customer_data = record.get_customers(record)
            # Order count query
            order_data = record.get_total_orders(record)
            # Order shipped count query
            order_shipped = record.get_shipped_orders(record)
            # # refund count query
            refund_data = record.get_refund(record)
            record.magento_order_data = json.dumps({
                "values": values,
                "title": "",
                "key": "Order: Untaxed amount",
                "area": True,
                "color": "#875A7B",
                "is_sample_data": False,
                "total_sales": total_sales,
                "order_data": order_data,
                "product_date": product_data,
                "customer_data": customer_data,
                "order_shipped": order_shipped,
                "refund_data": refund_data,
                "sort_on": self._context.get('sort'),
                "currency_symbol": '',  # record.magento_base_currency.symbol or '',
                # remove currency symbol and make it same as odoo
                "graph_sale_percentage": {'type': data_type, 'value': comparison_value}
            })

    def get_draft_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        website = context.get('website')
        result = self.get_refund(self, website, state)
        return result.get('refund_action')

    def get_posted_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        website = context.get('website')
        result = self.get_refund(self, website, state)
        return result.get('refund_action')

    def get_cancelled_refund(self):
        context = self.env.context
        state = f"('{context.get('state')}')"
        website = context.get('website')
        result = self.get_refund(self, website, state)
        return result.get('refund_action')

    def get_refund(self, instance, website_id=0, state=('draft', 'posted', 'cancel')):
        action = self.sudo().env.ref('odoo_magento2_ept.action_magento_refund_invoice_tree_ept')
        action = action.read()[0]
        if website_id:
            query = self._prepare_website_refund_query(website_id, instance, state)
        else:
            query = self._prepare_refund_query(instance, state)
        self._cr.execute(query)
        refunds = self._cr.dictfetchall()
        refund_ids = [refund.get('id') for refund in refunds]
        action = self.prepare_action(action, domain=[('id', 'in', refund_ids)])
        return {
            'refund_count': len(refund_ids),
            'refund_action': action
        }

    @staticmethod
    def _prepare_website_refund_query(website_id, instance, state):
        return f"""
        SELECT r.id 
            FROM account_move AS r
                JOIN account_move_line AS rl
                    ON r.id = rl.move_id
                JOIN sale_order_line_invoice_rel AS rel
                    ON rel.invoice_line_id = rl.id
                JOIN sale_order_line AS sl
                    ON rel.order_line_id = sl.id
                JOIN sale_order AS so
                    ON so.id = sl.order_id
                JOIN magento_instance AS mi
                    ON mi.id = so.magento_instance_id
                JOIN magento_website AS mw
                    ON mw.magento_instance_id = mi.id
            WHERE r.move_type = 'out_refund'
                AND mi.id = {website_id}
                AND mw.id = {instance.id}
                AND r.state in {state}
        """

    @staticmethod
    def _prepare_refund_query(instance, state=('draft', 'posted', 'cancel')):
        return f"""
        SELECT DISTINCT(id) 
            FROM account_move
            WHERE move_type = 'out_refund' 
                AND magento_instance_id = {instance.id}
                AND state in {state}
        """

    @staticmethod
    def prepare_action(view, domain):
        """
        Use: To prepare action dictionary
        :return: action details
        """
        action = {
            'name': view.get('name'),
            'type': view.get('type'),
            'domain': domain,
            'view_mode': view.get('view_mode'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'views': view.get('views'),
            'res_model': view.get('res_model'),
            'target': view.get('target'),
        }

        if 'tree' in action['views'][0]:
            action['views'][0] = (action['view_id'], 'list')
        return action

    def get_total_products(self, record, exported, product_type=False):
        """
        Use: To get the list of products exported from Magento instance
        Here if exported = True, then only get those record which having sync_product_with_magento= true
        if exported = False, then only get those record which having sync_product_with_magento= false
        if exported = All, then get all those records which having sync_product_with_magento = true and false
        :param record: magento website object
        :param exported: exported is one of the "True" or "False" or "All"
        :return: total number of Magento products ids and action for products
        """
        product_data = {}
        main_sql = """select count(id) as total_count from magento_product_template where
        magento_product_template.magento_instance_id = %s""" % (record.id)
        domain = []
        if exported != 'All' and exported:
            main_sql = main_sql + " and magento_product_template.sync_product_with_magento = True"
            domain.append(('sync_product_with_magento', '=', True))
        elif not exported:
            main_sql = main_sql + " and magento_product_template.sync_product_with_magento = False"
            domain.append(('sync_product_with_magento', '=', False))
        elif exported == 'All':
            domain.append(('sync_product_with_magento', 'in', (False, True)))

        if product_type:
            domain.append(('product_type', '=', product_type))
        self._cr.execute(main_sql)
        result = self._cr.dictfetchall()
        total_count = 0
        if result:
            total_count = result[0].get('total_count')
        view = self.env.ref('odoo_magento2_ept.action_magento_product_exported_ept').sudo().read()[
            0]
        domain.append(('magento_instance_id', '=', record.id))
        action = record.prepare_action(view, domain)
        product_data.update({'product_count': total_count, 'product_action': action})
        return product_data

    def get_customers(self, record):
        """
        Use: To get the list of customers with Magento instance for current Magento instance
        :return: total number of customer ids and action for customers
        """
        customer_data = {}
        main_sql = """select DISTINCT(rp.id) as partner_id from res_partner as rp
                    inner join magento_res_partner_ept mp on mp.partner_id = rp.id
                    where mp.magento_instance_id = %s""" % (record.id)
        view = self.env.ref('base.action_partner_form').sudo().read()[0]
        self._cr.execute(main_sql)
        result = self._cr.dictfetchall()
        magento_customer_ids = []
        if result:
            for data in result:
                magento_customer_ids.append(data.get('partner_id'))
        action = record.prepare_action(view, [('id', 'in', magento_customer_ids)])
        customer_data.update(
            {'customer_count': len(magento_customer_ids), 'customer_action': action})
        return customer_data

    def get_total_orders(self, record, state=False):
        """
        Use: To get the list of Magento sale orders month wise or year wise
        :return: total number of Magento sale orders ids and action for sale orders of current instance
        """
        if not state:
            state = ('sale', 'done')

        def orders_of_current_week(record):
            self._cr.execute("""select id from sale_order where date(date_order)
                                    >= (select date_trunc('week', date(current_date)))
                                    and magento_instance_id= %s and state in %s  
                                    order by date(date_order)
                            """ % (record.id, state))
            return self._cr.dictfetchall()

        def orders_of_current_month(record):
            self._cr.execute("""select id from sale_order where date(date_order) >=
                                    (select date_trunc('month', date(current_date)))
                                    and magento_instance_id= %s and state in %s
                                    order by date(date_order)
                            """ % (record.id, state))
            return self._cr.dictfetchall()

        def orders_of_current_year(record):
            self._cr.execute("""select id from sale_order where date(date_order) >=
                                    (select date_trunc('year', date(current_date))) 
                                    and magento_instance_id= %s and state in %s  
                                    order by date(date_order)
                                 """ % (record.id, state))
            return self._cr.dictfetchall()

        def orders_of_all_time(record):
            self._cr.execute(
                """select id from sale_order where magento_instance_id = %s
                and state in %s""" % (record.id, state))
            return self._cr.dictfetchall()

        order_data = {}
        order_ids = []
        if self._context.get('sort') == "week":
            result = orders_of_current_week(record)
        elif self._context.get('sort') == "month":
            result = orders_of_current_month(record)
        elif self._context.get('sort') == "year":
            result = orders_of_current_year(record)
        else:
            result = orders_of_all_time(record)
        if result:
            for data in result:
                order_ids.append(data.get('id'))
        view = self.env.ref('odoo_magento2_ept.magento_action_sales_order_ept').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def get_shipped_orders(self, record):
        """
        Use: To get the list of Magento shipped orders month wise or year wise
        :return: total number of Magento shipped orders ids and action for shipped orders of current instance
        """
        shipped_query = """
           SELECT distinct(so.id) 
           FROM stock_picking AS sp
           JOIN sale_order AS so
               ON sp.sale_id = so.id
           JOIN stock_location AS sl 
               ON sl.id = sp.location_dest_id 
           WHERE 
               sp.is_magento_picking = True AND 
               sp.state = 'done' AND
               so.magento_instance_id = {} AND
               sl.usage='customer'
       """.format(record.id)

        def shipped_order_of_current_week(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('week', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_current_month(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('month', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_current_year(shipped_query):
            qry = shipped_query + " and date(so.date_order) >= (select date_trunc('year', date(current_date)))"
            self._cr.execute(qry)
            return self._cr.dictfetchall()

        def shipped_order_of_all_time(shipped_query):
            self._cr.execute(shipped_query)
            return self._cr.dictfetchall()

        order_data = {}
        order_ids = []
        if self._context.get('sort') == "week":
            result = shipped_order_of_current_week(shipped_query)
        elif self._context.get('sort') == "month":
            result = shipped_order_of_current_month(shipped_query)
        elif self._context.get('sort') == "year":
            result = shipped_order_of_current_year(shipped_query)
        else:
            result = shipped_order_of_all_time(shipped_query)
        if result:
            for data in result:
                order_ids.append(data.get('id'))
        view = self.env.ref('odoo_magento2_ept.magento_action_sales_order_ept').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    def magento_product_exported_ept(self):
        """
        get exported as true product action
        :return:
        """
        exported = True
        product_data = self.get_total_products(self, exported)
        return product_data.get('product_action')

    def action_magento_simple_product_type(self):
        """
        get magento simple product type
        :return:
        """
        product_type = "simple"
        exported = "All"
        product_data = self.get_total_products(self, exported, product_type)
        return product_data.get('product_action')

    def action_magento_configurable_product_type(self):
        """
        get magento configurable product type
        :return:
        """
        product_type = "configurable"
        exported = "All"
        product_data = self.get_total_products(self, exported, product_type)
        return product_data.get('product_action')

    def magento_action_sales_quotations_ept(self):
        """
        get quotations action
        :return:
        """
        state = ('draft', 'sent')
        order_data = self.get_total_orders(self, state)
        return order_data.get('order_action')

    def magento_action_sales_order_ept(self):
        """
        get sales order action
        :return:
        """
        state = ('sale', 'done')
        order_data = self.get_total_orders(self, state)
        return order_data.get('order_action')

    def get_magento_invoice_records(self, state):
        """
        To get instance wise magento invoice
        :param state: state of the invoice
        :return: invoice_data dict with total count and action
        """
        invoice_data = {}
        invoice_ids = []
        invoice_query = """select account_move.id
            from sale_order_line_invoice_rel
            inner join sale_order_line on sale_order_line.id=sale_order_line_invoice_rel.order_line_id 
            inner join sale_order on sale_order.id=sale_order_line.order_id
            inner join account_move_line on account_move_line.id=sale_order_line_invoice_rel.invoice_line_id 
            inner join account_move on account_move.id=account_move_line.move_id
            where sale_order.magento_instance_id=%s
            and account_move.state in ('%s')
            and account_move.move_type in ('out_invoice','out_refund')""" % \
                        (self.id, state)
        self._cr.execute(invoice_query)
        result = self._cr.dictfetchall()
        view = self.env.ref('odoo_magento2_ept.action_magento_invoice_tree1_ept').sudo().read()[0]
        if result:
            for data in result:
                invoice_ids.append(data.get('id'))
        action = self.prepare_action(view, [('id', 'in', invoice_ids)])
        invoice_data.update({'order_count': len(invoice_ids), 'order_action': action})
        return invoice_data

    def get_magento_picking_records(self, state):
        """
        To get instance wise magento picking
        :param state: state of the picking
        :return: picking_data dict with total count and action
        """
        picking_data = {}
        picking_ids = []
        invoice_query = """SELECT SP.id FROM stock_picking as SP
            inner join sale_order as SO on SP.sale_id = SO.id
            inner join stock_location as SL on SL.id = SP.location_dest_id 
            WHERE SP.magento_instance_id = %s
            and SL.usage = 'customer'
            and SP.state in ('%s')
            """ % (self.id, state)
        self._cr.execute(invoice_query)
        result = self._cr.dictfetchall()
        view = \
            self.env.ref('odoo_magento2_ept.action_magento_stock_picking_tree_ept').sudo().read()[0]
        if result:
            for data in result:
                picking_ids.append(data.get('id'))
        action = self.prepare_action(view, [('id', 'in', picking_ids)])
        picking_data.update({'order_count': len(picking_ids), 'order_action': action})
        return picking_data

    def magento_invoice_invoices_open(self):
        """
        get draft state invoice action
        :return:
        """
        state = 'draft'
        invoice_data = self.get_magento_invoice_records(state)
        return invoice_data.get('order_action')

    def magento_invoice_invoices_paid(self):
        """
        get posted state invoice action
        :return:
        """
        state = 'posted'
        invoice_data = self.get_magento_invoice_records(state)
        return invoice_data.get('order_action')

    def magento_waiting_stock_picking_ept(self):
        """
        get confirmed state picking action
        :return:
        """
        state = 'confirmed'
        picking_data = self.get_magento_picking_records(state)
        return picking_data.get('order_action')

    def magento_partially_available_stock_picking_ept(self):
        """
        get partially_available state picking action
        :return:
        """
        state = 'partially_available'
        picking_data = self.get_magento_picking_records(state)
        return picking_data.get('order_action')

    def magento_ready_stock_picking_ept(self):
        """
        get assigned state picking action
        :return:
        """
        state = 'assigned'
        picking_data = self.get_magento_picking_records(state)
        return picking_data.get('order_action')

    def magento_transferred_stock_picking_ept(self):
        """
        get done state picking action
        :return:
        """
        state = 'done'
        picking_data = self.get_magento_picking_records(state)
        return picking_data.get('order_action')

    @api.model
    def perform_operation(self, record_id):
        """
        Use: To prepare Magento operation action
        :return: Magento operation action details
        """
        view = self.env.ref('odoo_magento2_ept.'
                            'action_wizard_magento_instance_import_export_operations').sudo().read()[
            0]
        action = self.prepare_action(view, [])
        action.update({'context': {'default_magento_instance_id': record_id}})
        return action

    @api.model
    def open_logs(self, record_id):
        """
        Use: To prepare Magento logs action
        :return: Magento logs action details
        """
        view = self.env.ref('odoo_magento2_ept.action_common_log_book_ept_magento').sudo().read()[0]
        return self.prepare_action(view, [('magento_instance_id', '=', record_id)])

    @api.model
    def open_report(self, record_id):
        """
        Use: To prepare Magento report action
        :return: Magento report action details
        """
        view = self.env.ref('odoo_magento2_ept.magento_sale_report_action_dashboard').sudo().read()[
            0]
        action = self.prepare_action(view, [('magento_instance_id', '=', record_id)])
        action.update(
            {'context': {'search_default_magento_instances': record_id, 'search_default_Sales': 1,
                         'search_default_filter_date': 1}})
        return action

    def get_graph_data(self, record):
        """
        Use: To get the details of Magento sale orders and total amount month wise or year wise to prepare the graph
        :return: Magento sale order date or month and sum of sale orders amount of current instance
        """

        def get_current_week_date(record):
            self._cr.execute("""SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
                                    FROM  (
                                       SELECT day
                                       FROM generate_series(date(date_trunc('week', (current_date)))
                                        , date(date_trunc('week', (current_date)) + interval '6 days')
                                        , interval  '1 day') day
                                       ) d
                                    LEFT   JOIN 
                                    (SELECT date(date_order)::date AS day, sum(amount_untaxed) as amount_untaxed
                                       FROM   sale_order
                                       WHERE  date(date_order) >= (select date_trunc('week', date(current_date)))
                                       AND    date(date_order) <= (select date_trunc('week', date(current_date)) 
                                       + interval '6 days')
                                       AND magento_instance_id=%s and state in ('sale','done')  
                                       GROUP  BY 1
                                       ) t USING (day)
                                    ORDER  BY day""" % (record.id))
            return self._cr.dictfetchall()

        def graph_of_current_month(record):
            self._cr.execute("""select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
                            SELECT 
                              day::date as date_day,
                              0 as amount_untaxed
                            FROM generate_series(date(date_trunc('month', (current_date)))
                                , date(date_trunc('month', (current_date)) + interval '1 MONTH - 1 day')
                                , interval  '1 day') day
                            union all
                            SELECT date(date_order)::date AS date_day,
                            sum(amount_untaxed) as amount_untaxed
                              FROM   sale_order
                            WHERE  date(date_order) >= (select date_trunc('month', date(current_date)))
                            AND date(date_order)::date <= (select date_trunc('month', date(current_date)) 
                            + '1 MONTH - 1 day')
                            and magento_instance_id = %s and state in ('sale','done')
                            group by 1
                            )foo 
                            GROUP  BY 1
                            ORDER  BY 1""" % (record.id))
            return self._cr.dictfetchall()

        def graph_of_current_year(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                    (SELECT DATE_TRUNC('month',date(day)) as month,
                                      0 as amount_untaxed
                                    FROM generate_series(date(date_trunc('year', (current_date)))
                                    , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                    , interval  '1 MONTH') day
                                    union all
                                    SELECT DATE_TRUNC('month',date(date_order)) as month,
                                    sum(amount_untaxed) as amount_untaxed
                                      FROM   sale_order
                                    WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND 
                                    date(date_order)::date <= (select date_trunc('year', date(current_date)) 
                                    + '1 YEAR - 1 day')
                                    and magento_instance_id = %s and state in ('sale','done') 
                                    group by DATE_TRUNC('month',date(date_order))
                                    order by month
                                    )foo 
                                    GROUP  BY foo.month
                                    order by foo.month""" % (record.id))
            return self._cr.dictfetchall()

        def graph_of_all_time(record):
            self._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                    from sale_order where magento_instance_id = %s and state in ('sale','done')  
                                    group by DATE_TRUNC('month',date_order) 
                                    order by DATE_TRUNC('month',date_order)""" % (record.id))
            return self._cr.dictfetchall()

        # Prepare values for Graph
        values = []
        if self._context.get('sort') == 'week':
            result = get_current_week_date(record)
        elif self._context.get('sort') == "month":
            result = graph_of_current_month(record)
        elif self._context.get('sort') == "year":
            result = graph_of_current_year(record)
        else:
            result = graph_of_all_time(record)
        if result:
            for data in result:
                values.append({"x": ("{}".format(data.get(list(data.keys())[0]))),
                               "y": data.get('sum') or 0.0})
        return values

    def get_compare_data(self, record):
        """
        :param record: Magento instance
        :return: Comparison ratio of orders (weekly,monthly and yearly based on selection)
        """
        data_type = False
        total_percentage = 0.0

        if self._context.get('sort') == 'week':
            current_total, previous_total = self.get_compared_week_data(record)
        elif self._context.get('sort') == "month":
            current_total, previous_total = self.get_compared_month_data(record)
        elif self._context.get('sort') == "year":
            current_total, previous_total = self.get_compared_year_data(record)
        else:
            current_total, previous_total = 0.0, 0.0
        if current_total > 0.0:
            if current_total >= previous_total:
                data_type = 'positive'
                total_percentage = (current_total - previous_total) * 100 / current_total
            if previous_total > current_total:
                data_type = 'negative'
                total_percentage = (previous_total - current_total) * 100 / current_total
        return data_type, round(total_percentage, 2)

    def get_compared_week_data(self, record):
        current_total = 0.0
        previous_total = 0.0
        day_of_week = date.weekday(date.today())
        self._cr.execute("""select sum(amount_untaxed) as current_week from sale_order
                                where date(date_order) >= (select date_trunc('week', date(current_date))) and
                                magento_instance_id=%s and state in ('sale','done')""" %
                         (record.id))
        current_week_data = self._cr.dictfetchone()
        if current_week_data and current_week_data.get('current_week'):
            current_total = current_week_data.get('current_week')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_week from sale_order
                            where date(date_order) between (select date_trunc('week', current_date) - interval '7 day') 
                            and (select date_trunc('week', (select date_trunc('week', current_date) - interval '7
                            day')) + interval '%s day')
                            and magento_instance_id=%s and state in ('sale','done')
                            """ % (day_of_week, record.id))
        previous_week_data = self._cr.dictfetchone()
        if previous_week_data and previous_week_data.get(
                'previous_week'):
            previous_total = previous_week_data.get('previous_week')
        return current_total, previous_total

    def get_compared_month_data(self, record):
        current_total = 0.0
        previous_total = 0.0
        day_of_month = date.today().day - 1
        self._cr.execute("""select sum(amount_untaxed) as current_month from sale_order
                                where date(date_order) >= (select date_trunc('month', date(current_date)))
                                and magento_instance_id=%s and state in ('sale','done')""" %
                         (record.id))
        current_data = self._cr.dictfetchone()
        if current_data and current_data.get('current_month'):
            current_total = current_data.get('current_month')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_month from sale_order where date(date_order)
                            between (select date_trunc('month', current_date) - interval '1 month') and
                            (select date_trunc('month', (select date_trunc('month', current_date) - interval
                            '1 month')) + interval '%s days')
                            and magento_instance_id=%s and state in ('sale','done')
                            """ % (day_of_month, record.id))
        previous_data = self._cr.dictfetchone()
        if previous_data and previous_data.get('previous_month'):
            previous_total = previous_data.get('previous_month')
        return current_total, previous_total

    def get_compared_year_data(self, record):
        current_total = 0.0
        previous_total = 0.0
        year_begin = date.today().replace(month=1, day=1)
        year_end = date.today()
        delta = (year_end - year_begin).days - 1
        self._cr.execute("""select sum(amount_untaxed) as current_year from sale_order
                                where date(date_order) >= (select date_trunc('year', date(current_date)))
                                and magento_instance_id=%s and state in ('sale','done')""" %
                         (record.id))
        current_data = self._cr.dictfetchone()
        if current_data and current_data.get('current_year'):
            current_total = current_data.get('current_year')
        # Previous week data
        self._cr.execute("""select sum(amount_untaxed) as previous_year from sale_order where date(date_order)
                            between (select date_trunc('year', date(current_date) - interval '1 year')) and 
                            (select date_trunc('year', date(current_date) - interval '1 year') + interval '%s days') 
                            and magento_instance_id=%s and state in ('sale','done')
                            """ % (delta, record.id))
        previous_data = self._cr.dictfetchone()
        if previous_data and previous_data.get('previous_year'):
            previous_total = previous_data.get('previous_year')
        return current_total, previous_total

    def create_common_log_book(self, process_type, module_name):
        """ This method used to create a log book record.
            @param process_type: Generally, the process type value is 'import' or 'export'.
            @param module_name: Model related to log, like create a sales order related log
            then pass the sales order model.
        """
        model_id = self.env['common.log.lines.ept'].get_model_id(module_name)
        return self.env["common.log.book.ept"].create_common_log_book(
            process_type, 'magento_instance_id', self, model_id, 'magento_ept')

    def create_schedule_activity(self, queue, note):
        if queue.process_count == 3 and queue.instance_id.is_create_activity:
            self.create_activity(model_name=queue._name, res_id=queue.id, message=note,
                                 summary=queue.name, instance=queue.instance_id)
            queue.write({'is_action_require': True})
            # Commit the record to reduce concurrent issue.
            self._cr.commit()
        return True

    def create_activity(self, **kwargs):
        model_id = self._get_model_id(model_name=kwargs.get('model_name'))
        activities = self._prepare_activity_values(model_id=model_id, **kwargs)
        mail_activity = self.sudo().env['mail.activity']
        for activity in activities:
            mail_activity.create(activity)
        return True

    def _get_model_id(self, model_name):
        model_id = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
        if model_id:
            model_id = model_id.id
        return model_id

    def _prepare_activity_values(self, **kwargs):
        instance = kwargs.get('instance')
        type_id = kwargs.get('instance', self.env['magento.instance']).activity_type.id
        values = list()
        for user in instance.activity_user_ids:
            _logger.info("Schedule Activity Created...")
            values.append({
                'activity_type_id': type_id,
                'user_id': user.id,
                'res_id': kwargs.get('res_id'),
                'res_model_id': kwargs.get('model_id'),
                'summary': kwargs.get('summary'),
                'note': kwargs.get('message'),
                'date_deadline': datetime.now() + timedelta(days=instance.activity_lead_days)
            })
        return values

    def show_popup_notification(self, message):
        self.env["bus.bus"]._sendone(self.env.user.partner_id, 'simple_notification', {
            "title": "Magento Connector",
            "message": message,
            "sticky": False,
            "warning": True
        })
        return True

    def get_draft_queues(self, model='', name=''):
        if not model:
            return False
        query = f"""
            SELECT queue_id 
                FROM {model} 
                WHERE 
                    state = 'draft'
                GROUP BY queue_id, create_date
                ORDER BY create_date ASC
            """
        self._cr.execute(query)
        queue_ids = [queue.get('queue_id') for queue in self._cr.dictfetchall()]
        # model = model.replace('_', '.')
        queues = self.env[name].browse(queue_ids)
        return queues.filtered(lambda q: not q.is_action_require)

    def get_queue_action(self, ids, **kwargs):
        """
        it's return the tree view or form view based on the total_customer_queues.
        :param ids: customer queue ids
        :return: view with domain
        """
        if not ids:
            return False
        action = {
            'name': kwargs.get('name'),
            'res_model': kwargs.get('model'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
        }
        if len(ids) > 1:
            action.update({'domain': [('id', 'in', ids)]})
        else:
            view_id = self.env.ref(kwargs.get('action')).id
            action.update({
                'views': [(view_id, 'form')],
                'view_id': view_id,
                'view_mode': 'form',
                'res_id': ids[0],
                'target': 'current'
            })
        return action

    def create_log_book(self, model='magento.instance', p_type='import', **kwargs):
        model_id = self.env['common.log.lines.ept'].get_model_id(model)
        return self.env["common.log.book.ept"].create({
            'model_id': model_id,
            'type': p_type,
            'active': True,
            'res_id': kwargs.get('res_id'),
            'module': 'magento_ept',
            'magento_instance_id': self.id
        })

    def create_log_line(self, **kwargs):
        log_line = self.env['common.log.lines.ept']
        model_id = log_line.get_model_id(kwargs.get('model'))
        return log_line.create({
            'model_id': model_id,
            'default_code': kwargs.get('default_code', ''),
            'log_book_id': kwargs.get('log_id', False),
            'message': kwargs.get('message', ''),
            'res_id': kwargs.get('res_id'),
            'mismatch_details': kwargs.get('mismatch', True),
            'log_line_type': 'fail',
            'order_ref': kwargs.get('order_ref', '')
        })
