# See LICENSE file for full copyright and licensing details.
"""For Odoo Magento2 Connector Module"""
from odoo import models, fields


class IrCron(models.Model):
    """Inherited for identifying Magento's cron."""
    _inherit = 'ir.cron'

    magento_product_import_cron = fields.Boolean('Magento Product Cron')
    magento_import_order_cron = fields.Boolean('Magento Order Cron')
    magento_instance_id = fields.Many2one('magento.instance', string="Cron Scheduler")
    do_not_update_existing_product = fields.Boolean(
        string="Do not update existing Products?",
        help="If checked and Product(s) found in odoo/Magento layer, then not update the Product(s)",
        default=False
    )