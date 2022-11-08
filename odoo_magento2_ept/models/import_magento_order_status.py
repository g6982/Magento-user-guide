# See LICENSE file for full copyright and licensing details.
"""
Describes fields for importing magento order status
"""
from odoo import models, fields


class ImportMagentoOrderStatus(models.Model):
    """
    Describes fields for importing magento order status
    """
    _name = "import.magento.order.status"
    _description = 'Order Status'

    name = fields.Char(string="Magento Status Name")
    status = fields.Char(string="Magento Order Status")
