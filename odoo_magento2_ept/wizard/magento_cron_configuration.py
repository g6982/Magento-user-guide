# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields and methods for Magento Cron Configuration
"""
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
RES_USERS = 'res.users'
IMPORT_SALE_ORDER_CRON = 'odoo_magento2_ept.ir_cron_import_shipped_sale_orders_instance_id_%d'
IMPORT_UNSHIPPED_SALE_ORDER_CRON = 'odoo_magento2_ept.ir_cron_import_unshipped_sale_orders_instance_id_%d'
IMPORT_CANCEL_SALE_ORDER_CRON = 'odoo_magento2_ept.ir_cron_import_cancel_sale_orders_instance_id_%d'
EXPORT_PRODUCT_STOCK_CRON = 'odoo_magento2_ept.ir_cron_export_product_stock_qty_instance_id_%d'
EXPORT_SHIPMENT_ORDER_STATUS_CRON = 'odoo_magento2_ept.ir_cron_export_shipment_order_status_instance_id_%d'
EXPORT_INVOICE_CRON = 'odoo_magento2_ept.ir_cron_export_invoice_instance_id_%d'
IMPORT_MAGENTO_PRODUCT_CRON = 'odoo_magento2_ept.ir_cron_import_magento_product_instance_id_%d'
CRON_ERROR_MSG = 'Core settings of Magento are deleted, please upgrade Magento module to back this settings.'
MAGENTO_STR = 'Magento - '
IR_MODEL_DATA = 'ir.model.data'
IR_CRON = 'ir.cron'

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class MagentoCronConfiguration(models.TransientModel):
    """
    Describes fields and methods for Magento Cron Configuration
    """
    _name = "magento.cron.configuration"
    _description = "Magento Cron Configuration"

    def _get_magento_instance(self):
        return self.env.context.get('magento_instance_id', False)

    magento_instance_id = fields.Many2one(
        'magento.instance',
        string='Magento Instance',
        default=_get_magento_instance,
        readonly=True
    )

    # Auto import Product
    auto_import_product = fields.Boolean(
        string='Auto import product?',
        help="Auto Automatic Import Product"
    )
    auto_import_product_interval_number = fields.Integer(
        string='Auto Import Product Interval Numbers',
        help="Import product every x interval.",
        default=1
    )
    auto_import_product_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Import Product Interval Unit', help='Auto Import Product Interval Unit')
    auto_import_product_next_execution = fields.Datetime(
        string='Auto Next Product Execution',
        help='Next execution time for import product'
    )
    auto_import_product_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Import Product User',
        help="Responsible User for import product"
    )
    do_not_update_existing_product = fields.Boolean(
        string="Do not update existing Products?",
        help="If checked and Product(s) found in odoo/Magento layer, then not update the Product(s)",
        default=False
    )

    # Auto import sale orders
    auto_import_sale_orders = fields.Boolean(
        string='Auto import sale orders?',
        help="Automatic Import Shipped Sale Orders"
    )
    auto_import_sale_orders_interval_number = fields.Integer(
        string='Auto Import sale orders Interval Number',
        help="Import sale order every x interval.",
        default=1
    )
    auto_import_sale_orders_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Import Sale Order Interval Unit', help='Auto Import Sale Order Interval Unit')
    auto_import_sale_orders_next_execution = fields.Datetime(
        string='Auto Next Sale Execution',
        help='Next execution time for import sale order'
    )
    auto_import_sale_order_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Import Shipped Sale Order User',
        help="Responsible User for import sale order"
    )

    # Auto import sale orders
    auto_import_unshipped_sale_orders = fields.Boolean(
        string='Auto import Unshipped sale orders?',
        help="Automatic Import Sale Orders"
    )
    auto_import_unshipped_sale_orders_interval_number = fields.Integer(
        string='Auto Import Unshipped sale orders Interval Number',
        help="Import sale order every x interval.",
        default=1
    )
    auto_import_unshipped_sale_orders_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Import Unshipped Sale Order Interval Unit', help='Auto Import Sale Order Interval Unit')
    auto_import_unshipped_sale_orders_next_execution = fields.Datetime(
        string='Auto Next Unshipped Sale Execution',
        help='Next execution time for import sale order'
    )
    auto_import_unshipped_sale_order_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Import Unshipped Sale Order User',
        help="Responsible User for import sale order"
    )

    # Auto import cancel sale orders
    auto_import_cancel_sale_orders = fields.Boolean(
        string='Auto cancel import sale orders?',
        help="Automatic Cancel Import Sale Orders"
    )
    auto_import_cancel_sale_orders_interval_number = fields.Integer(
        string='Auto Import Cancel sale orders Interval Number',
        help="Import cancel sale order every x interval.",
        default=1
    )
    auto_import_cancel_sale_orders_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Import Cancel Sale Order Interval Unit', help='Auto Import Cancel Sale Order Interval Unit')
    auto_import_cancel_sale_orders_next_execution = fields.Datetime(
        string='Auto Next Cancel Sale Execution',
        help='Next execution time for import Cancel sale order'
    )
    auto_import_cancel_sale_order_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Import Cancel Sale Order User',
        help="Responsible User for import Cancel sale order"
    )

    # Auto Export Product Stock
    auto_export_product_stock = fields.Boolean(
        string='Auto Export Product Stock?',
        help="Automatic Export Product Stock"
    )
    auto_export_product_stock_interval_number = fields.Integer(
        string='Auto Export Product Stock Interval Numbers',
        help="Export product stock every x interval.",
        default=1
    )
    auto_export_product_stock_interval_type = fields.Selection(
        [
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months')
        ],
        string='Auto Import Product Stock Interval Unit',
        help='Auto Import Product Stock Interval Unit'
    )
    auto_export_product_stock_next_execution = fields.Datetime(
        string='Auto Next Export Product Execution',
        help='Next execution time for export product stock'
    )
    auto_export_product_stock_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Export Product User',
        help="Responsible User for export product stock"
    )

    # Auto Export Invoice
    auto_export_invoice = fields.Boolean(
        string='Auto Export Invoice?',
        help="Auto Automatic Export Invoice"
    )
    auto_export_invoice_interval_number = fields.Integer(
        string='Auto Export Invoice Interval Numbers',
        help="Export Invoice every x interval.",
        default=1
    )
    auto_export_invoice_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Export Invoice  Interval Unit', help='Auto Export Invoice  Interval Unit')
    auto_export_invoice_next_execution = fields.Datetime(
        string='Auto Next Export Invoice  Execution',
        help='Next execution time for export invoice'
    )
    auto_export_invoice_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Export Invoice User',
        help="Responsible User for export invoice"
    )

    # Auto Export Shipment Information
    auto_export_shipment_order_status = fields.Boolean(
        string='Auto Export Shipment Information?',
        help="Automatic Export Shipment Information"
    )
    auto_export_shipment_order_status_interval_number = fields.Integer(
        string='Auto Update Order Status Interval Number',
        help="Export shipment every x interval.",
        default=1
    )
    auto_export_shipment_order_status_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Auto Export Shipment Interval Unit', help='Auto Export Shipment Interval Unit')
    auto_export_shipment_order_status_next_execution = fields.Datetime(
        string='Auto Next Order Status Execution',
        help='Next execution time for export shipment'
    )
    auto_export_shipment_order_status_user_id = fields.Many2one(
        RES_USERS,
        string='Auto Update Order User',
        help="Responsible User for export shipment"
    )

    @api.onchange("magento_instance_id")
    def onchange_magento_instance_id(self):
        """
        This method is used to set cron configuration on change of Instance.
        :return:
        """
        magento_instance = self.magento_instance_id
        self.magento_import_sale_order_cron_field(magento_instance)
        self.magento_import_unshipped_sale_order_cron_field(magento_instance)
        self.magento_import_cancel_sale_order_cron_field(magento_instance)
        self.export_product_stock_cron_field(magento_instance)
        self.export_shipment_order_cron_field(magento_instance)
        self.export_invoice_cron_field(magento_instance)
        self.import_magento_product_cron_field(magento_instance)

    def magento_import_sale_order_cron_field(self, instance):
        """
        This method is used to set import sale order cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            magento_import_order_cron_exist = instance and self.env.ref(
                IMPORT_SALE_ORDER_CRON % instance.id
            )
        except Exception:
            magento_import_order_cron_exist = False
        if magento_import_order_cron_exist:
            interval_number = magento_import_order_cron_exist.interval_number or False
            interval_type = magento_import_order_cron_exist.interval_type or False
            nextcall = magento_import_order_cron_exist.nextcall or False
            user_id = magento_import_order_cron_exist.user_id.id or False
            self.auto_import_sale_orders = magento_import_order_cron_exist.active or False
            self.auto_import_sale_orders_interval_number = interval_number
            self.auto_import_sale_orders_interval_type = interval_type
            self.auto_import_sale_orders_next_execution = nextcall
            self.auto_import_sale_order_user_id = user_id

    def magento_import_unshipped_sale_order_cron_field(self, instance):
        """
        This method is used to set import sale order cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            magento_import_unshipped_order_cron_exist = instance and self.env.ref(
                IMPORT_UNSHIPPED_SALE_ORDER_CRON % instance.id
            )
        except Exception:
            magento_import_unshipped_order_cron_exist = False
        if magento_import_unshipped_order_cron_exist:
            interval_number = magento_import_unshipped_order_cron_exist.interval_number or False
            interval_type = magento_import_unshipped_order_cron_exist.interval_type or False
            nextcall = magento_import_unshipped_order_cron_exist.nextcall or False
            user_id = magento_import_unshipped_order_cron_exist.user_id.id or False
            self.auto_import_unshipped_sale_orders = magento_import_unshipped_order_cron_exist.active or False
            self.auto_import_unshipped_sale_orders_interval_number = interval_number
            self.auto_import_unshipped_sale_orders_interval_type = interval_type
            self.auto_import_unshipped_sale_orders_next_execution = nextcall
            self.auto_import_unshipped_sale_order_user_id = user_id

    def magento_import_cancel_sale_order_cron_field(self, instance):
        """
        This method is used to set import cancel sale order cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            magento_import_cancel_order_cron_exist = instance and self.env.ref(
                IMPORT_CANCEL_SALE_ORDER_CRON % instance.id
            )
        except Exception:
            magento_import_cancel_order_cron_exist = False
        if magento_import_cancel_order_cron_exist:
            interval_number = magento_import_cancel_order_cron_exist.interval_number or False
            interval_type = magento_import_cancel_order_cron_exist.interval_type or False
            nextcall = magento_import_cancel_order_cron_exist.nextcall or False
            user_id = magento_import_cancel_order_cron_exist.user_id.id or False
            self.auto_import_cancel_sale_orders = magento_import_cancel_order_cron_exist.active or False
            self.auto_import_cancel_sale_orders_interval_number = interval_number
            self.auto_import_cancel_sale_orders_interval_type = interval_type
            self.auto_import_cancel_sale_orders_next_execution = nextcall
            self.auto_import_cancel_sale_order_user_id = user_id

    def export_product_stock_cron_field(self, instance):
        """
        This method is used to set export product stock cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            magento_export_product_stock_cron_exist = instance and self.env.ref(
                EXPORT_PRODUCT_STOCK_CRON % instance.id
            )
        except Exception:
            magento_export_product_stock_cron_exist = False
        if magento_export_product_stock_cron_exist:
            interval_number = magento_export_product_stock_cron_exist.interval_number or False
            interval_type = magento_export_product_stock_cron_exist.interval_type or False
            nextcall = magento_export_product_stock_cron_exist.nextcall or False
            user_id = magento_export_product_stock_cron_exist.user_id.id or False
            self.auto_export_product_stock = magento_export_product_stock_cron_exist.active or False
            self.auto_export_product_stock_interval_number = interval_number
            self.auto_export_product_stock_interval_type = interval_type
            self.auto_export_product_stock_next_execution = nextcall
            self.auto_export_product_stock_user_id = user_id

    def export_shipment_order_cron_field(self, instance):
        """
        This method is used to set export shipment order cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            export_shipment_order_cron_exist = instance and self.env.ref(
                EXPORT_SHIPMENT_ORDER_STATUS_CRON % instance.id
            )
        except Exception:
            export_shipment_order_cron_exist = False
        if export_shipment_order_cron_exist:
            export_shipment_order_cron_active = export_shipment_order_cron_exist.active
            interval_number = export_shipment_order_cron_exist.interval_number or False
            interval_type = export_shipment_order_cron_exist.interval_type or False
            nextcall = export_shipment_order_cron_exist.nextcall or False
            user_id = export_shipment_order_cron_exist.user_id.id or False
            self.auto_export_shipment_order_status = export_shipment_order_cron_active or False
            self.auto_export_shipment_order_status_interval_number = interval_number
            self.auto_export_shipment_order_status_interval_type = interval_type
            self.auto_export_shipment_order_status_next_execution = nextcall
            self.auto_export_shipment_order_status_user_id = user_id

    def export_invoice_cron_field(self, magento_instance):
        """
        This method is used to set export invoice cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        try:
            export_invoice_cron_exist = magento_instance and self.env.ref(
                EXPORT_INVOICE_CRON % (magento_instance.id)
            )
        except Exception:
            export_invoice_cron_exist = False
        if export_invoice_cron_exist:
            interval_number = export_invoice_cron_exist.interval_number or False
            interval_type = export_invoice_cron_exist.interval_type or False
            self.auto_export_invoice = export_invoice_cron_exist.active or False
            self.auto_export_invoice_interval_number = interval_number
            self.auto_export_invoice_interval_type = interval_type
            self.auto_export_invoice_next_execution = export_invoice_cron_exist.nextcall or False
            self.auto_export_invoice_user_id = export_invoice_cron_exist.user_id.id or False

    def import_magento_product_cron_field(self, instance):
        """
        This method is used to set import magento product cron
        :param instance:  Instance of Magento
        :return:
        """
        try:
            import_product_cron_exist = instance and self.env.ref(
                IMPORT_MAGENTO_PRODUCT_CRON % instance.id
            )
        except Exception:
            import_product_cron_exist = False
        if import_product_cron_exist:
            interval_number = import_product_cron_exist.interval_number or False
            interval_type = import_product_cron_exist.interval_type or False
            self.auto_import_product = import_product_cron_exist.active or False
            self.auto_import_product_interval_number = interval_number
            self.auto_import_product_interval_type = interval_type
            self.auto_import_product_next_execution = import_product_cron_exist.nextcall or False
            self.auto_import_product_user_id = import_product_cron_exist.user_id.id or False
            self.do_not_update_existing_product = import_product_cron_exist.do_not_update_existing_product

    def save_cron_configuration(self):
        """
        This method is used to save all cron configurations
        :return:
        """
        ir_action_obj = self.env["ir.actions.actions"]
        magento_instance = self.magento_instance_id
        vals = {}
        self.auto_import_sale_order(magento_instance)
        self.auto_import_unshipped_sale_order(magento_instance)
        self.auto_import_cancel_sale_order(magento_instance)
        self.auto_export_product_stock_qty(magento_instance)
        self.auto_export_shipment_order_status_cron(magento_instance)
        self.auto_export_invoice_cron(magento_instance)
        self.auto_import_magento_product_cron(magento_instance)
        vals['auto_import_sale_orders'] = self.auto_import_sale_orders or False
        vals['auto_import_unshipped_sale_orders'] = self.auto_import_unshipped_sale_orders or False
        vals['auto_import_cancel_sale_orders'] = self.auto_import_cancel_sale_orders or False
        vals['auto_export_product_stock'] = self.auto_export_product_stock or False
        vals['auto_export_shipment_order_status'] = self.auto_export_shipment_order_status or False
        vals['auto_export_invoice'] = self.auto_export_invoice or False
        vals['auto_import_product'] = self.auto_import_product or False
        self.env['magento.api.request.page'].update_magento_order_page_count_users_vise(magento_instance)
        magento_instance.write(vals)
        # Below code is used for only onboarding panel purpose.
        if self._context.get('is_calling_from_magento_onboarding_panel', False):
            action = ir_action_obj._for_xml_id(
                "odoo_magento2_ept.magento_onboarding_confirmation_wizard_action")
            action['context'] = {'magento_instance_id': magento_instance.id}
            return action
        return True

    def auto_import_sale_order(self, magento_instance):
        """
        This method is used to create import sale order cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_import_sale_orders:
            cron_exist = self.env.ref(
                IMPORT_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            auto_import_sale_order_user_id = self.auto_import_sale_order_user_id
            vals = {
                "active": True,
                "interval_number": self.auto_import_sale_orders_interval_number,
                "interval_type": self.auto_import_sale_orders_interval_type,
                "nextcall": self.auto_import_sale_orders_next_execution,
                "code": "model._scheduler_import_shipped_sale_orders({'magento_instance_id' : %d})" % magento_instance.id,
                "user_id": auto_import_sale_order_user_id and auto_import_sale_order_user_id.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                import_sale_orders_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_import_shipped_sale_orders',
                    raise_if_not_found=False
                )
                if not import_sale_orders_cron:
                    raise UserError(_(CRON_ERROR_MSG))
                name = MAGENTO_STR + magento_instance.name + ' : Import Shipped Sale Orders'
                vals.update({'name': name})
                new_cron = import_sale_orders_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_import_shipped_sale_orders_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                IMPORT_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_import_unshipped_sale_order(self, magento_instance):
        """
        This method is used to create import sale order cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_import_unshipped_sale_orders:
            cron_exist = self.env.ref(
                IMPORT_UNSHIPPED_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            auto_import_unshipped_sale_order_user_id = self.auto_import_unshipped_sale_order_user_id
            vals = {
                "active": True,
                "interval_number": self.auto_import_unshipped_sale_orders_interval_number,
                "interval_type": self.auto_import_unshipped_sale_orders_interval_type,
                "nextcall": self.auto_import_unshipped_sale_orders_next_execution,
                "code": "model._scheduler_import_unshipped_sale_orders({'magento_instance_id' : %d})" % magento_instance.id,
                "user_id": auto_import_unshipped_sale_order_user_id and auto_import_unshipped_sale_order_user_id.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                import_unshipped_sale_orders_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_import_unshipped_sale_orders',
                    raise_if_not_found=False
                )
                if not import_unshipped_sale_orders_cron:
                    raise UserError(_(CRON_ERROR_MSG))
                name = MAGENTO_STR + magento_instance.name + ' : Import Unshipped Sale Orders'
                vals.update({'name': name})
                new_cron = import_unshipped_sale_orders_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_import_unshipped_sale_orders_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                IMPORT_UNSHIPPED_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_import_cancel_sale_order(self, magento_instance):
        """
        This method is used to create import cancel sale order cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_import_cancel_sale_orders:
            cron_exist = self.env.ref(
                IMPORT_CANCEL_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            auto_import_cancel_sale_order_user_id = self.auto_import_cancel_sale_order_user_id
            vals = {
                "active": True,
                "interval_number": self.auto_import_cancel_sale_orders_interval_number,
                "interval_type": self.auto_import_cancel_sale_orders_interval_type,
                "nextcall": self.auto_import_cancel_sale_orders_next_execution,
                "code": "model._scheduler_import_cancel_sale_orders({'magento_instance_id' : %d})" % magento_instance.id,
                "user_id": auto_import_cancel_sale_order_user_id and auto_import_cancel_sale_order_user_id.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                import_cancel_sale_orders_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_import_cancel_sale_orders',
                    raise_if_not_found=False
                )
                if not import_cancel_sale_orders_cron:
                    raise UserError(_(CRON_ERROR_MSG))
                name = MAGENTO_STR + magento_instance.name + ' : Import Cancel Sale Orders'
                vals.update({'name': name})
                new_cron = import_cancel_sale_orders_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_import_cancel_sale_orders_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                IMPORT_CANCEL_SALE_ORDER_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_export_product_stock_qty(self, magento_instance):
        """
        This method is used to create export product stock quantity cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_export_product_stock:
            cron_exist = self.env.ref(
                EXPORT_PRODUCT_STOCK_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            auto_export_product_stock_user = self.auto_export_product_stock_user_id
            vals = {
                "active": True,
                "interval_number": self.auto_export_product_stock_interval_number,
                "interval_type": self.auto_export_product_stock_interval_type,
                "nextcall": self.auto_export_product_stock_next_execution,
                "code": "model._scheduler_update_product_stock_qty({'magento_instance_id' : %d})" % (
                    magento_instance.id),
                "user_id": auto_export_product_stock_user and auto_export_product_stock_user.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                export_product_stock_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_export_product_stock_qty',
                    raise_if_not_found=False
                )
                if not export_product_stock_cron:
                    raise UserError(_(CRON_ERROR_MSG))

                name = MAGENTO_STR + magento_instance.name + ' : Auto Export Stock'
                vals.update({'name': name})
                new_cron = export_product_stock_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_export_product_stock_qty_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                EXPORT_PRODUCT_STOCK_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_export_shipment_order_status_cron(self, magento_instance):
        """
        This method is used to create export shipment order status cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_export_shipment_order_status:
            cron_exist = self.env.ref(
                EXPORT_SHIPMENT_ORDER_STATUS_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            export_ship_order_status_user = self.auto_export_shipment_order_status_user_id
            vals = {
                "active": True,
                "interval_number": self.auto_export_shipment_order_status_interval_number,
                "interval_type": self.auto_export_shipment_order_status_interval_type,
                "nextcall": self.auto_export_shipment_order_status_next_execution,
                "code": "model._scheduler_update_order_status({'magento_instance_id' : %d})" % magento_instance.id,
                "user_id": export_ship_order_status_user and export_ship_order_status_user.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                update_order_status_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_export_shipment_order_status',
                    raise_if_not_found=False
                )
                if not update_order_status_cron:
                    raise UserError(_(CRON_ERROR_MSG))

                name = MAGENTO_STR + magento_instance.name + ' : Export Shipment Information'
                vals.update({'name': name})
                new_cron = update_order_status_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_export_shipment_order_status_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                EXPORT_SHIPMENT_ORDER_STATUS_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_export_invoice_cron(self, magento_instance):
        """
        This method is used to create export invoice cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_export_invoice:
            cron_exist = self.env.ref(
                EXPORT_INVOICE_CRON % magento_instance.id,
                raise_if_not_found=False
            )

            vals = {
                "active": True,
                "interval_number": self.auto_export_invoice_interval_number,
                "interval_type": self.auto_export_invoice_interval_type,
                "nextcall": self.auto_export_invoice_next_execution,
                "code": "model._scheduler_export_invoice({'magento_instance_id' : %d})" % magento_instance.id,
                "user_id": self.auto_export_invoice_user_id and self.auto_export_invoice_user_id.id,
                "magento_instance_id": magento_instance.id
            }

            if cron_exist:
                cron_exist.write(vals)
            else:
                export_inovice_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_export_invoice',
                    raise_if_not_found=False
                )
                if not export_inovice_cron:
                    raise UserError(_(CRON_ERROR_MSG))

                name = MAGENTO_STR + magento_instance.name + ' : Export Invoice'
                vals.update({'name': name})
                new_cron = export_inovice_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_export_invoice_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                EXPORT_INVOICE_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def auto_import_magento_product_cron(self, magento_instance):
        """
        This method is used to create import magento product cron
        :param magento_instance:  Instance of Magento
        :return:
        """
        if self.auto_import_product:
            cron_exist = self.env.ref(
                IMPORT_MAGENTO_PRODUCT_CRON % magento_instance.id,
                raise_if_not_found=False)

            vals = {
                "active": True,
                "interval_number": self.auto_import_product_interval_number,
                "interval_type": self.auto_import_product_interval_type,
                "nextcall": self.auto_import_product_next_execution,
                "code": "model._scheduler_import_product({'magento_instance_id' : %d, 'update_existing_product': %s})" % (magento_instance.id, self.do_not_update_existing_product),
                "user_id": self.auto_import_product_user_id and self.auto_import_product_user_id.id,
                "magento_instance_id": magento_instance.id,
                "do_not_update_existing_product": self.do_not_update_existing_product
            }
            if cron_exist:
                cron_exist.write(vals)
            else:
                export_inovice_cron = self.env.ref(
                    'odoo_magento2_ept.ir_cron_import_magento_product',
                    raise_if_not_found=False
                )
                if not export_inovice_cron:
                    raise UserError(_(CRON_ERROR_MSG))

                name = MAGENTO_STR + magento_instance.name + ' : Import Product'
                vals.update({'name': name})
                new_cron = export_inovice_cron.copy(default=vals)
                self.env[IR_MODEL_DATA].create({
                    'module': 'odoo_magento2_ept',
                    'name': 'ir_cron_import_magento_product_instance_id_%d' % magento_instance.id,
                    'model': IR_CRON,
                    'res_id': new_cron.id,
                    'noupdate': True
                })
        else:
            cron_exist = self.env.ref(
                IMPORT_MAGENTO_PRODUCT_CRON % magento_instance.id,
                raise_if_not_found=False
            )
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    @api.model
    def action_magento_open_cron_configuration_wizard(self):
        """
        Called by onboarding panel above the Instance.
        Return the action for open the cron configuration wizard
        :return: True
        """
        magento_instance_obj = self.env['magento.instance']
        ir_action_obj = self.env["ir.actions.actions"]
        action = ir_action_obj._for_xml_id(
            "odoo_magento2_ept.action_magento_wizard_cron_configuration_ept")
        instance = magento_instance_obj.search_magento_instance()
        action['context'] = {'is_calling_from_magento_onboarding_panel': True}
        if instance:
            action.get('context').update({'default_magento_instance_id': instance.id,
                                          'is_instance_exists': True})
        return action

    def check_core_magento_cron(self, name):
        """
        This method will check for the core cron and if doesn't exist, then raise error.
        @author: Nikul Alagiya on Date 18-Jul-2022.
        @param name: Name of the core cron.
        """
        try:
            core_cron = self.env.ref(name)
        except:
            core_cron = False

        if not core_cron:
            raise UserError(_(CRON_ERROR_MSG))
        return core_cron
