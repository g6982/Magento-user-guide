# -*- coding: utf-8 -*-

import odoo
from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    magento_instance_id = fields.Many2one('magento.instance', 'Magento Instance', readonly=True)
    magento_website_id = fields.Many2one('magento.website', 'Magento Website', readonly=True)

    def _query(self, with_clause='', field=None, groupby='', from_clause=''):
        """
        Add Magento instance field in model group by
        :param with_clause:
        :param field: magento_instance_id, magento_website_id
        :param groupby:magento_instance_id, magento_website_id
        :param from_clause:
        :return:
        """
        if field is None:
            field = {}
        field['magento_instance_id'] = ", s.magento_instance_id as magento_instance_id"
        field['magento_website_id'] = ", s.magento_website_id as magento_website_id"
        groupby += ', s.magento_instance_id , s.magento_website_id'
        return super()._query(with_clause, field, groupby, from_clause)

    def magento_sale_report(self):
        """ Base on the odoo version it return the action.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29 September 2020 .
            @modify : Hardik Dhankecha 11/Nov/2021
            Task_id: 167120
        """
        version_info = odoo.service.common.exp_version()
        if version_info.get('server_version') == '15.0':
            action = self.env.ref('odoo_magento2_ept.magento_action_order_report_all').read()[0]
        else:
            action = self.env.ref('odoo_magento2_ept.magento_sale_report_action_dashboard').read()[0]

        return action
