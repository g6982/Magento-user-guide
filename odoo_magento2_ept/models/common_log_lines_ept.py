# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes new fields and methods for common log lines
"""
from odoo import models, fields


class CommonLogLineEpt(models.Model):
    """
    Describes common log book line
    """
    _inherit = "common.log.lines.ept"

    magento_order_data_queue_line_id = fields.Many2one(
        string="Order Queue Line", comodel_name="magento.order.data.queue.line.ept")
    import_product_queue_line_id = fields.Many2one(
        string="Product Queue Line", comodel_name="sync.import.magento.product.queue.line")
    magento_customer_data_queue_line_id = fields.Many2one(
        string="Customer Queue Line", comodel_name="magento.customer.data.queue.line.ept")
    magento_export_stock_queue_line_id = fields.Many2one(
        string="Export Stock Queue Line", comodel_name="magento.export.stock.queue.line.ept")
