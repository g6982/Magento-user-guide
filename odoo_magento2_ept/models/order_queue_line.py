# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store Order Data queue line
"""
import json
import pytz
import time
from odoo import models, fields, _
from dateutil import parser

utc = pytz.utc


class MagentoOrderDataQueueLineEpt(models.Model):
    """
    Describes Order Data Queue Line
    """
    _name = "magento.order.data.queue.line.ept"
    _description = "Magento Order Data Queue Line EPT"
    _rec_name = "magento_id"

    queue_id = fields.Many2one(comodel_name="magento.order.data.queue.ept", ondelete="cascade")
    instance_id = fields.Many2one(comodel_name='magento.instance', string='Magento Instance',
                                  help="Order imported from this Magento Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"), ("done", "Done"),
                              ("cancel", "Cancelled")], default="draft", copy=False)
    magento_id = fields.Char(string="Magento Order#", help="Id of imported order.", copy=False)
    sale_order_id = fields.Many2one(comodel_name="sale.order", copy=False,
                                    help="Order created in Odoo.")
    data = fields.Text(help="Data imported from Magento of current order.", copy=False)
    processed_at = fields.Datetime(string="Processed At", copy=False,
                                   help="Shows Date and Time, When the data is processed")
    log_lines_ids = fields.One2many("common.log.lines.ept", "magento_order_data_queue_line_id",
                                    help="Log lines created against which line.")

    def open_sale_order(self):
        """
        call this method while click on > Order Data Queue line > Sale Order smart button
        :return: Tree view of the odoo sale order
        """
        return {
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.sale_order_id.id)]
        }

    def create_order_queue_line(self, instance, order, queue):
        self.create({
            'magento_id': order.get('increment_id'),
            'instance_id': instance.id,
            'data': json.dumps(order),
            'queue_id': queue.id
        })
        return True

    def auto_import_order_queue_data(self):
        """
        This method used to process synced magento order data in batch of 50 queue lines.
        This method is called from cron job.
        """
        queues = self.instance_id.get_draft_queues(model='magento_order_data_queue_line_ept',
                                                   name=self.queue_id._name)
        queues.process_order_queues()

    def process_order_queue_line(self, line, log):
        item = json.loads(line.data)
        order_ref = item.get('increment_id')
        order = self.env['sale.order']
        instance = self.instance_id
        is_exists = order.search([('magento_instance_id', '=', instance.id),
                                  ('magento_order_reference', '=', order_ref)])
        if is_exists:
            return True
        create_at = item.get("created_at", False)
        # Need to compare the datetime object
        date_order = parser.parse(create_at).astimezone(utc).strftime("%Y-%m-%d %H:%M:%S")
        if str(instance.import_order_after_date) > date_order:
            message = _(f"""
            There is a configuration mismatch in the import of order #{order_ref}.\n
            The order receive date is {date_order}.\n
            Please check the date set in the configuration in Magento2 Connector -> Configuration 
            -> Setting -> Select Instance -> 'Import Order After Date'.
            """)
            log.write({'log_lines': [(0, 0, {
                'message': message, 'order_ref': line.magento_id,
                'magento_order_data_queue_line_id': line.id
            })]})
            return False
        is_processed = self.financial_status_config(item, instance, log, line)
        if is_processed:
            carrier = self.env['delivery.carrier']
            is_processed = carrier.find_delivery_carrier(item, instance, log, line)
            if is_processed:
                # add create product method
                item_ids = self.__prepare_product_dict(item.get('items'))
                m_product = self.env['magento.product.product']
                p_items = m_product.with_context(is_order=True).get_products(instance, item_ids, line)

                order_item = self.env['sale.order.line'].find_order_item(item, instance, log, line.id)
                if not order_item:
                    if p_items:
                        p_queue = self.env['sync.import.magento.product.queue.line']
                        self._update_product_type(p_items, item)
                        for p_item in p_items:
                            is_processed = p_queue.with_context(is_order=True).import_products(p_item, line)
                            if not is_processed:
                                break
                    else:
                        is_processed = False
                if is_processed:
                    is_processed = order.create_sale_order_ept(item, instance, log, line.id)
                    if is_processed:
                        line.write({'sale_order_id': item.get('sale_order_id').id})
        return is_processed

    @staticmethod
    def __prepare_product_dict(items):
        parent_id, item_ids = [], []
        for item in items:
            e_attribute = item.get('extension_attributes', {})
            product_id = item.get('product_id')
            if e_attribute.get('simple_parent_id'):
                product_id = e_attribute.get('simple_parent_id')
            if product_id not in item_ids:
                item_ids.append(product_id)
        return item_ids

    @staticmethod
    def _update_product_type(p_items, items):
        for p_item in p_items:
            for item in items.get('items'):
                if item.get('product_id') == p_item.get('id'):
                    p_item.update({
                        'type_id': item.get('product_type'),
                        'increment_id': items.get('increment_id')
                    })
        return True

    def financial_status_config(self, item, instance_id, log, line):
        is_processed = True
        f_status = self.env['magento.financial.status.ept']
        method = item.get('payment', dict()).get('method')
        gateway = instance_id.payment_method_ids.filtered(
            lambda x: x.payment_method_code == method)
        payment_name = gateway.payment_method_name
        f_status = f_status.search_financial_status(item, instance_id, gateway)
        workflow = f_status.get('workflow')
        status_name = f_status.get('status_name')
        message = ''
        if workflow and not status_name:
            is_processed, message = self.check_mismatch_order(item)
        elif not workflow:
            is_processed = False
            message = _(f"""
            - No automatic order process workflow configuration was found 
            for this order {item.get('increment_id')}.\n
            - Based on the combination of Payment Gateway (such as Bank Transfer, etc.) 
            the system attempts to determine the workflow. \n
            - In this order, Payment Gateway is '{payment_name}' and Financial Status 
            is {status_name} Orders. \n
            - Automatic order process workflow can be configured under the  
            Magento -> Configuration > Financial Status.
            """)
        elif status_name and not workflow.auto_workflow_id:
            is_processed = False
            message = _(f"""
            Order {item.get('increment_id')} was skipped because the auto workflow configuration  
            was not found for payment method - '{payment_name}' and financial 
            status - {status_name} Orders.
            """)
        elif status_name and not workflow.payment_term_id:
            is_processed = False
            message = _(f"""
            Order {item.get('increment_id')} was skipped because Payment Term was not found
            for payment method - {method} and financial status - {status_name} Orders. 
            """)
        if not is_processed:
            log.write({'log_lines': [(0, 0, {
                'message': message, 'order_ref': line.magento_id,
                'magento_order_data_queue_line_id': line.id
            })]})
        else:
            item.update({
                'workflow_id': workflow.auto_workflow_id,
                'payment_term_id': workflow.payment_term_id,
                'payment_gateway': gateway.id
            })
        return is_processed

    @staticmethod
    def check_mismatch_order(item):
        is_inv = item.get('extension_attributes').get('is_invoice')
        is_ship = item.get('extension_attributes').get('is_shipment')
        if not is_inv and not is_ship and item.get('status') == 'processing':
            message = _(f"""
            Order {item.get('increment_id')} was skipped, Order status is processing, 
            but the order is neither invoice nor shipped.
            """)
        elif item.get('status') not in ['pending', 'processing', 'complete']:
            message = _("""
            Order {item.get('increment_id')} was skipped due to financial status not found of 
            order status {item.get('status')}.\n 
            Currently the Magento2 Odoo Connector supports magento default order status 
            such as 'Pending', 'Processing' and 'Completed'.
            The connector does not support the magento2 custom order status {item.get('status')}. 
            """)
        else:
            message = _("""
            Order {item.get('increment_id')} was skipped because the order is partially invoiced
            and partially shipped.\n Magento order status Processing: Processing means that orders
            have either been invoiced or shipped, but not both.\n In this, we are receiving
            order in which it is partially invoiced and partially shipped.   
            """)
        return False, message
