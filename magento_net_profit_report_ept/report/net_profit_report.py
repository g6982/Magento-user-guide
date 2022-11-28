# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportAccountFinancialReportExtended(models.Model):
    _inherit = "account.financial.html.report"

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(ReportAccountFinancialReportExtended, self)._get_options(previous_options)

        # If manual values were stored in the context, we store them as options.
        # This is useful for report printing, were relying only on the context is
        # not enough, because of the use of a route to download the report (causing
        # a context loss, but keeping the options).
        # if self._context.get('financial_report_line_values'):
        #     options['financial_report_line_values'] = self.env.context['financial_report_line_values']
        if self._context.get('magento_report'):
            magento_instance_ids = self.env['magento.instance'].search([('active', '=', 'True')])
            if magento_instance_ids:
                options.update(
                    {
                        'analytic_accounts': magento_instance_ids.magento_website_ids.m_website_analytic_account_id.ids or magento_instance_ids.mapped(
                            'magento_analytic_account_id').ids,
                        'analytic_tags': magento_instance_ids.magento_website_ids.m_website_analytic_tag_ids.ids or magento_instance_ids.mapped(
                            'magento_analytic_tag_ids').ids})
        return options
