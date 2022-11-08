# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields for common log book.
"""
from odoo import models, fields


class CommonLogBookEpt(models.Model):
    """
    Describes Common log book
    """
    _inherit = "common.log.book.ept"
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          help="Magento Instance.")

    def create_order_log_lines(self, message, order_ref, order_data_queue_line_id):
        """
        Create log lines for common log book object
        :param message: Error message
        :param order_ref: Order reference
        :param order_data_queue_line_id: Order queue data line object
        :return:
        """
        self.write({
            'log_lines': [(0, 0, {
                'message': message,
                'order_ref': order_ref,
                'magento_order_data_queue_line_id': order_data_queue_line_id
            })]
        })

    def add_log_line(self, message, order_ref,
                     order_data_queue_line_id, queue_line, sku=False):
        """
        Create new log line based on the product queue and order queue
        If queue_line = order data queue then set order_ref = False
        :param message: Message of the log line
        :param order_ref: reference of the order
        :param order_data_queue_line_id: queue line ID
        :param queue_line: import_product_queue_line_id or magento_order_data_queue_line_id
        :param sku: product SKU
        :return: log line id
        """
        self.write({
            'log_lines': [(0, 0, {
                'message': message,
                'order_ref': order_ref if queue_line == 'magento_order_data_queue_line_id' else '',
                queue_line: order_data_queue_line_id,
                'default_code': sku
            })]
        })
        return self.id
