# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes fields and methods for create/ update sale order
"""
import json
import pytz
import time
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .api_request import req
from dateutil import parser

utc = pytz.utc

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
SALE_ORDER_LINE = 'sale.order.line'


class SaleOrder(models.Model):
    """
    Describes fields and methods for create/ update sale order
    """
    _inherit = 'sale.order'

    def _get_magento_order_status(self):
        """
        Compute updated_in_magento of order from the pickings.
        """
        for order in self:
            if order.magento_instance_id:
                pickings = order.picking_ids.filtered(lambda x: x.state != "cancel")
                stock_moves = order.order_line.move_ids.filtered(
                    lambda x: not x.picking_id and x.state == 'done')
                if pickings:
                    outgoing_picking = pickings.filtered(
                        lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("is_exported_to_magento")):
                        order.updated_in_magento = True
                        continue
                if stock_moves:
                    order.updated_in_magento = True
                    continue
                order.updated_in_magento = False
                continue
            order.updated_in_magento = False

    def _search_magento_order_ids(self, operator, value):
        query = """select so.id from stock_picking sp
                    inner join sale_order so on so.procurement_group_id=sp.group_id                   
                    inner join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer'
                    where sp.is_exported_to_magento %s true and sp.state != 'cancel'
                    """ % operator
        if operator == '=':
            query += """union all
                    select so.id from sale_order as so
                    inner join sale_order_line as sl on sl.order_id = so.id
                    inner join stock_move as sm on sm.sale_line_id = sl.id
                    where sm.picking_id is NULL and sm.state = 'done' and so.magento_instance_id notnull"""
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id', 'in', order_ids)]

    magento_instance_id = fields.Many2one(
        'magento.instance',
        string="Instance",
        help="This field relocates Magento Instance"
    )
    magento_order_id = fields.Char(string="Magento order Ids", help="Magento Order Id")
    magento_website_id = fields.Many2one(
        "magento.website",
        string="Magento Website",
        help="Magento Website"
    )
    magento_order_reference = fields.Char(
        string="Magento Orders Reference",
        help="Magento Order Reference"
    )
    store_id = fields.Many2one(
        'magento.storeview',
        string="Magento Storeview",
        help="Magento_store_view"
    )
    is_exported_to_magento_shipment_status = fields.Boolean(
        string="Is Order exported to Shipment Status",
        help="Is exported to Shipment Status"
    )
    magento_payment_method_id = fields.Many2one(
        'magento.payment.method',
        string="Magento Payment Method",
        help="Magento Payment Method"
    )
    magento_shipping_method_id = fields.Many2one(
        'magento.delivery.carrier',
        string="Magento Shipping Method",
        help="Magento Shipping Method"
    )
    order_transaction_id = fields.Char(
        string="Magento Orders Transaction ID",
        help="Magento Orders Transaction ID"
    )
    updated_in_magento = fields.Boolean(
        string="Order fulfilled in magento", compute="_get_magento_order_status",
        search="_search_magento_order_ids",
        copy=False
    )

    _sql_constraints = [('_magento_sale_order_unique_constraint',
                         'unique(magento_order_id,magento_instance_id,magento_order_reference)',
                         "Magento order must be unique")]

    def _cancel_order_exportable(self):
        """
        this method will check order is cancel in odoo or not, and invoice is exported or not.
        And shipment done in magento or not
        :return:
        """
        if (self.invoice_ids and True in self.invoice_ids.mapped('is_exported_to_magento')) or \
                (self.picking_ids and self.picking_ids.filtered(
                    lambda x: x.state == 'done' and x.is_exported_to_magento).ids):
            self.is_cancel_order_exportable = True
        else:
            self.is_cancel_order_exportable = False

    is_cancel_order_exportable = fields.Boolean(string="Is Invoice exportable",
                                                compute='_cancel_order_exportable',
                                                store=False)

    def create_sale_order_ept(self, item, instance, log, line_id):
        is_processed = self._find_price_list(item, log, line_id, instance)
        order_line = self.env['sale.order.line']
        if is_processed:
            customers = self.__update_partner_dict(item, instance)
            data = self.env['magento.res.partner.ept'].create_magento_customer(customers, True)
            item.update(data)
            is_processed = self.__find_order_warehouse(item, log, line_id)
            if is_processed:
                is_processed = order_line.find_order_item(item, instance, log, line_id)
                if is_processed:
                    is_processed = self.__find_order_tax(item, instance, log, line_id)
                    if is_processed:
                        vals = self._prepare_order_dict(item, instance)
                        magento_order = self.create(vals)
                        item.update({'sale_order_id': magento_order})
                        order_line.create_order_line(item, instance, log, line_id)
                        self.__create_discount_order_line(item, instance)
                        self.__create_shipping_order_line(item, instance)
                        self.__process_order_workflow(item, log)
        return is_processed

    @staticmethod
    def __find_order_warehouse(item, log, line_id):
        is_processed = True
        if not item.get('website').warehouse_id.id:
            message = _(f"""
            Order {item['increment_id']} was skipped because warehouse is not set for the website 
            {item['website'].name}. Please configure it from Magento2 Connector -> Configuration -> 
            Setting -> Magento websites.
            """)
            log.write({'log_lines': [(0, 0, {
                'message': message, 'order_ref': item['increment_id'],
                'magento_order_data_queue_line_id': line_id
            })]})
            is_processed = False
        return is_processed

    def _find_price_list(self, item, log, line_id, instance):
        is_processed = True
        currency = item.get('base_currency_code') if instance.is_order_base_currency else item.get(
            'order_currency_code')
        currency_id = self._find_currency(currency)
        price_list = self.env['product.pricelist'].search([('currency_id', '=', currency_id.id)])
        if price_list:
            price_list = price_list[0]
            item.update({'price_list_id': price_list})
        elif not price_list or price_list.currency_id != currency_id:
            price_list = self.env['product.pricelist'].create({
                'name': " Pricelist - " + currency,
                'currency_id': currency_id.id,
                'discount_policy': 'with_discount',
                'company_id': self.company_id.id,
            })
            item.update({'price_list_id': price_list})
        return is_processed

    def _find_currency(self, currency_code):
        currency = self.env['res.currency']
        currency = currency.with_context(active_test=False).search([('name', '=', currency_code)],
                                                                   limit=1)
        if not currency.active:
            currency.write({'active': True})
        return currency

    def __update_partner_dict(self, item, instance):
        addresses = []
        magento_store = instance.magento_website_ids.store_view_ids.filtered(
            lambda l: l.magento_storeview_id == str(item.get('store_id')))
        m_customer_id = self.__get_customer_id(item)
        website_id = magento_store.magento_website_id.magento_website_id
        customers = {
            'instance_id': instance,
            'firstname': item.get('customer_firstname'),
            'lastname': item.get('customer_lastname'),
            'email': item.get('customer_email'),
            'website': magento_store.magento_website_id,
            'website_id': website_id and int(website_id) or '',
            'store_view': magento_store,
            'id': m_customer_id,
            'is_guest': item.get('customer_is_guest'),
            'is_faulty': not item.get('customer_is_guest') and not item.get('customer_id', False),
        }
        if item.get('customer_is_guest'):
            customers.update({
                'firstname': item.get('billing_address').get('firstname'),
                'lastname': item.get('billing_address').get('lastname'),
            })
        b_address = self.__update_partner_address_dict(customers, item.get('billing_address'))
        addresses.append(b_address)
        ship_assign = item.get('extension_attributes', dict()).get('shipping_assignments')
        for ship_addr in ship_assign:
            if isinstance(ship_addr, dict) and 'address' in list(
                    ship_addr.get('shipping', {}).keys()):
                ship_addr = ship_addr.get('shipping', dict()).get('address')
                s_address = self.__update_partner_address_dict(customers, ship_addr)
                addresses.append(s_address)
        customers.update({'addresses': addresses})
        item.update(customers)
        return customers

    @staticmethod
    def __get_customer_id(item):
        customer_id = item.get('customer_id', False)
        if item.get('customer_is_guest'):
            customer_id = "Guest Customer"
        elif not item.get('customer_is_guest') and not item.get('customer_id', False):
            customer_id = "Customer Without Id"
        return customer_id

    @staticmethod
    def __update_partner_address_dict(item, addresses):
        address = {
            'firstname': addresses.get('firstname'),
            'lastname': addresses.get('lastname'),
            'email': item.get('email'),
            'street': addresses.get('street'),
            'city': addresses.get('city'),
            'postcode': addresses.get('postcode'),
            'company': addresses.get('company', False),
            'id': addresses.get('customer_address_id') or addresses.get('entity_id'),
            'website_id': item.get('website_id'),
            'customer_id': item.get('id'),
            'region': {
                "region_code": addresses.get('region_code')
            },
            'vat_id': addresses.get('vat_id'),
            'country_id': addresses.get('country_id'),
            'telephone': addresses.get('telephone')
        }
        if addresses.get('address_type') == 'billing':
            address.update({'default_billing': True})
        if addresses.get('address_type') == 'shipping':
            address.update({'default_shipping': True})
        return address

    def _prepare_order_dict(self, item, instance):
        store_view = item.get('store_view')
        order_vals = {
            'company_id': instance.company_id.id,
            'partner_id': item.get('parent_id'),
            'partner_invoice_id': item.get('invoice'),
            'partner_shipping_id': item.get('delivery') if item.get('delivery') else item.get(
                'invoice'),
            'warehouse_id': item.get('website').warehouse_id.id,
            'picking_policy': item.get('workflow_id') and item.get(
                'workflow_id').picking_policy or False,
            'date_order': item.get('created_at', False),
            'pricelist_id': item.get('price_list_id') and item.get('price_list_id').id or False,
            'team_id': store_view and store_view.team_id and store_view.team_id.id or False,
            'payment_term_id': item.get('payment_term_id').id,
            'carrier_id': item.get('delivery_carrier_id'),
            'client_order_ref': item.get('increment_id')
        }
        order_vals = self.create_sales_order_vals_ept(order_vals)
        order_vals = self.__update_order_dict(item, instance, order_vals)
        return order_vals

    def __update_order_dict(self, item, instance, order_vals):
        payment_info = item.get('extension_attributes').get('order_response')
        store_view = item.get('store_view')
        website_id = store_view.magento_website_id
        magento_account = instance.magento_analytic_account_id.id if instance.magento_analytic_account_id else False
        if not magento_account:
            magento_account = store_view.magento_website_id.m_website_analytic_account_id.id if store_view.magento_website_id.m_website_analytic_account_id else False
        order_vals.update({
            'magento_instance_id': instance.id,
            'magento_website_id': website_id.id,
            'store_id': item.get('store_view').id,
            'auto_workflow_process_id': item.get('workflow_id') and item.get('workflow_id').id,
            'magento_payment_method_id': item.get('payment_gateway'),
            'magento_shipping_method_id': item.get('magento_carrier_id'),
            'is_exported_to_magento_shipment_status': False,
            'magento_order_id': item.get('entity_id'),
            'magento_order_reference': item.get('increment_id'),
            'order_transaction_id': self.__find_transaction_id(payment_info),
            'analytic_account_id': magento_account,
        })
        if store_view and not store_view.is_use_odoo_order_sequence:
            name = "%s%s" % (store_view and store_view.sale_prefix or '', item.get('increment_id'))
            order_vals.update({"name": name})
        return order_vals

    @staticmethod
    def __find_transaction_id(payment_info):
        payment_additional_info = payment_info if payment_info else False
        transaction_id = False
        if payment_additional_info:
            for payment_info in payment_additional_info:
                if payment_info.get('key') == 'transaction_id':
                    transaction_id = payment_info.get('value')
        return transaction_id

    def __create_shipping_order_line(self, item, instance):
        order_line = self.env['sale.order.line']
        incl_amount = float(item.get('base_shipping_incl_tax', 0.0)) if instance.is_order_base_currency else float(
            item.get('shipping_incl_tax', 0.0))
        excl_amount = float(item.get('base_shipping_amount', 0.0)) if instance.is_order_base_currency else float(
            item.get('shipping_amount', 0.0))
        sale_order_id = item.get('sale_order_id')
        if incl_amount or excl_amount:
            tax_type = self.__find_tax_type(item.get('extension_attributes'),
                                            'apply_shipping_on_prices')
            price = incl_amount if tax_type else excl_amount
            default_product = self.env.ref('odoo_magento2_ept.product_product_shipping')
            product = sale_order_id.magento_instance_id.shipping_product_id or default_product
            shipping_line = order_line.prepare_order_line_vals(item, {}, product, price)
            shipping_line.update({'is_delivery': True})
            if item.get('shipping_tax'):
                shipping_line.update({'tax_id': [(6, 0, item.get('shipping_tax'))]})
            order_line.create(shipping_line)
        return True

    def __find_shipping_tax_percent(self, tax_details, ext_attrs):
        if "item_applied_taxes" in ext_attrs:
            tax_type = self.__find_tax_type(ext_attrs, 'apply_shipping_on_prices')
            for order_res in ext_attrs.get("item_applied_taxes"):
                if order_res.get('type') == "shipping" and order_res.get('applied_taxes'):
                    for tax in order_res.get('applied_taxes', list()):
                        tax_details.append({
                            'line_tax': 'shipping_tax', 'tax_type': tax_type,
                            'tax_title': tax.get('title'),
                            'tax_percent': tax.get('percent', 0)})
        return tax_details

    def __find_tax_percent_title(self, item, instance):
        tax_details = []
        if instance.magento_apply_tax_in_order == 'create_magento_tax':
            if 'apply_discount_on_prices' in item.get('extension_attributes'):
                tax_type = self.__find_tax_type(item.get('extension_attributes'),
                                                'apply_discount_on_prices')
                tax_percent = self.__find_discount_tax_percent(item.get('items'))
                if tax_percent:
                    tax_name = '%s %% ' % tax_percent
                    tax_details.append(
                        {'line_tax': 'discount_tax', 'tax_type': tax_type, 'tax_title': tax_name,
                         'tax_percent': tax_percent})
            if 'apply_shipping_on_prices' in item.get('extension_attributes'):
                ext_attrs = item.get('extension_attributes')
                tax_details = self.__find_shipping_tax_percent(tax_details, ext_attrs)
            #else:
            for line in item.get('items'):
                tax_percent = line.get('tax_percent', 0.0)
                parent_item = line.get('parent_item', {})
                if parent_item and parent_item.get('product_type') != 'bundle':
                    tax_percent = line.get('parent_item', {}).get('tax_percent', 0.0)
                if tax_percent:
                    tax_name = '%s %% ' % tax_percent
                    tax_type = (item.get('website').tax_calculation_method == 'including_tax')
                    tax_details.append(
                        {'line_tax': f'order_tax_{line.get("item_id")}', 'tax_type': tax_type,
                         'tax_title': tax_name, 'tax_percent': tax_percent})
        return tax_details

    @staticmethod
    def __find_tax_type(ext_attrs, tax):
        tax_type = False
        if tax in ext_attrs:
            tax_price = ext_attrs.get(tax)
            if tax_price == 'including_tax':
                tax_type = True
        return tax_type

    def __create_discount_order_line(self, item, instance):
        order_line = self.env['sale.order.line']
        sale_order_id = item.get('sale_order_id')
        price = float(item.get('base_discount_amount') or 0.0) or False if instance.is_order_base_currency else float(
            item.get('discount_amount') or 0.0) or False
        if price:
            default_product = self.env.ref('odoo_magento2_ept.magento_product_product_discount')
            product = sale_order_id.magento_instance_id.discount_product_id or default_product
            line = order_line.prepare_order_line_vals(item, {}, product, price)
            if item.get('discount_tax'):
                line.update({'tax_id': [(6, 0, item.get('discount_tax'))]})
            order_line.create(line)
        return True

    @staticmethod
    def __find_discount_tax_percent(items):
        percent = False
        for item in items:
            percent = item.get('tax_percent') if 'tax_percent' in item.keys() and item.get(
                'tax_percent') > 0 else False
            if percent:
                break
        return percent

    def __find_order_tax(self, item, instance, log, line_id):
        order_line = self.env['sale.order.line']
        account_tax_obj = self.env['account.tax']
        tax_details = self.__find_tax_percent_title(item, instance)
        tax_id_list = []
        shipping_details = item.get('extension_attributes').get('shipping_assignments')[0].get('shipping').get(
            'address', False)
        if shipping_details:
            country_code = shipping_details.get('country_id')
            country_name = self.env['res.partner'].get_country(country_code)
        for tax in tax_details:
            tax_id = account_tax_obj.get_tax_from_rate(
                float(tax.get('tax_percent')), tax.get('tax_title'), tax.get('tax_type'), country_name)
            if tax_id and not tax_id.active:
                message = _(f"""
                Order {item['increment_id']} was skipped because the tax {tax_id.name}% was not found. 
                The connector is unable to create new tax {tax_id.name}%, kindly check the tax 
                {tax_id.name}% has been archived? 
                """)
                log.write({'log_lines': [(0, 0, {
                    'message': message, 'order_ref': item['increment_id'],
                    'magento_order_data_queue_line_id': line_id
                })]})
                return False
            if not tax_id:
                tax_vals = order_line.prepare_tax_dict(tax, instance)
                tax_id = account_tax_obj.sudo().create(tax_vals)
            if tax.get('line_tax') != 'shipping_tax':
                item.update({tax.get('line_tax'): tax_id.ids})
            else:
                tax_id_list.append(tax_id.id)
        if tax_id_list:
            item.update({'shipping_tax': tax_id_list})
        return True

    def __process_order_workflow(self, item, log):
        sale_workflow = self.env['sale.workflow.process.ept']
        sale_order = item.get('sale_order_id')
        if item.get('status') == 'complete' or \
                (item.get('status') == 'processing' and
                 item.get('extension_attributes').get('is_shipment')):
            sale_order.auto_workflow_process_id.with_context(
                log_book_id=log.id).shipped_order_workflow_ept(sale_order)
        else:
            sale_workflow.with_context(
                log_book_id=log.id).auto_workflow_process_ept(
                sale_order.auto_workflow_process_id.id, [sale_order.id])
        if item.get('status') == 'complete' or \
                (item.get('status') == 'processing' and
                 item.get('extension_attributes').get('is_invoice')) and \
                sale_order.invoice_ids:
            # Here the magento order is complete state or
            # processing state with invoice so invoice is already created
            # So Make the Export invoice as true to hide Export invoice button from invoice.
            sale_order.invoice_ids.write({'is_exported_to_magento': True})

    def cancel_order_from_magento(self):
        """
        this method will call while sale order cancel from webhook
        :return:
        """
        log_msg = ""
        result = False
        try:
            result = super(SaleOrder, self).action_cancel()
        except Exception as error:
            log_msg = error
        if not result:
            message = "Order {} could not be cancelled in Odoo via webhook. \n".format(
                self.magento_order_reference) + str(log_msg)
            model_id = self.env['common.log.lines.ept'].sudo().get_model_id('sale.order')
            self.env['common.log.book.ept'].sudo().create({
                'type': 'import',
                'module': 'magento_ept',
                'model_id': model_id,
                'res_id': self.id,
                'magento_instance_id': self.magento_instance_id.id,
                'log_lines': [(0, 0, {
                    'message': message,
                    'order_ref': self.name,
                })]
            })
        return True

    def import_cancel_order(self, **kwargs):
        """
        This method use for import cancel order from magento.
        @:return:result
        :return:
        """
        instance = kwargs.get('instance')
        order_queue = self.env['magento.order.data.queue.ept']
        orders = order_queue._get_order_response(instance, kwargs, False)
        for order in orders['items']:
            order_id = order.get('entity_id', 0)
            sale_order = self.search([('magento_instance_id', '=', instance.id),
                        ('magento_order_id', '=', str(order_id))], limit=1)
            if sale_order:
                sale_order.sudo().cancel_order_from_magento()
        return True

    def cancel_order_in_magento(self):
        """
        This method use for cancel order in magento.
        @return: result
        """
        result = super(SaleOrder, self).action_cancel()
        magento_order_id = self.magento_order_id
        if magento_order_id:
            magento_instance = self.magento_instance_id
            try:
                api_url = '/V1/orders/%s/cancel' % magento_order_id
                result = req(magento_instance, api_url, 'POST')
            except Exception:
                raise UserError("Error while requesting cancel order")
        return result

    def _prepare_invoice(self):
        """
        This method is used for set necessary value(is_magento_invoice,
        is_exported_to_magento,magento_instance_id) in invoice.
        :return:
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.magento_payment_method_id:
            invoice_vals['magento_payment_method_id'] = self.magento_payment_method_id.id
        if self.magento_instance_id:
            invoice_vals.update({
                'magento_instance_id': self.magento_instance_id.id,
                'is_magento_invoice': True,
                'is_exported_to_magento': False
            })
        return invoice_vals

    def open_order_in_magento(self):
        """
        This method is used for open order in magento
        """
        m_url = self.magento_instance_id.magento_admin_url
        m_order_id = self.magento_order_id
        if m_url:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s/sales/order/view/order_id/%s' % (m_url, m_order_id),
                'target': 'new',
            }
