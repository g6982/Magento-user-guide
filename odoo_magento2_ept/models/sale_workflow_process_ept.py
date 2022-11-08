# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class SaleWorkflowProcessEpt(models.Model):
    _inherit = "sale.workflow.process.ept"

    magento_order_type = fields.Many2one(comodel_name='import.magento.order.status',
                                         string='Magento Order Status',
                                         help="Select order status for that you want to create "
                                              "auto workflow.")
