# See LICENSE file for full copyright and licensing details.
"""
Describes methods for importing magento customers into Odoo.
"""
import logging
from odoo import models, fields, api

_logger = logging.getLogger("MagentoEPT")


class MagentoAPIRequestPage(models.Model):
    """
    Describes Magento Api Page wise request
    """
    _name = "magento.api.request.page"
    _description = "Magento API Request Page"

    magento_import_order_page_count = fields.Integer(string="Magento Import order Page Count",
                                                     default=1,
                                                     help="It will fetch order of Magento from given page numbers.")
    magento_instance_id = fields.Many2one(comodel_name='magento.instance',
                                          string='Magento Instance',
                                          help="Order imported from this Magento Instance.")
    user_id = fields.Many2one(comodel_name='res.users', string='Users', help="Active Users.")

    @api.model
    def update_magento_order_page_count_users_vise(self, magento_instances=False):
        if not magento_instances:
            magento_instances = self.env['magento.instance'].search([])
        for magento_instance in magento_instances:
            active_user = False
            active_order_cron = self.env.ref(
                'odoo_magento2_ept.ir_cron_import_sale_orders_instance_id_%d' % magento_instance.id,
                raise_if_not_found=False
            )
            if active_order_cron:
                active_user = active_order_cron.user_id
            if active_user:
                existing_page_count = self.search([
                    ('magento_instance_id', '=', magento_instance.id),
                    ('user_id', '=', active_user.id)], limit=1)
                if not existing_page_count:
                    self.create({
                        'magento_import_order_page_count': magento_instance.magento_import_order_page_count,
                        'magento_instance_id': magento_instance.id,
                        'user_id': active_user.id
                    })
        return True
