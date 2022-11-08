# -*- coding: utf-8 -*-
"""
Onboarding Controller.
"""
from odoo import http
from odoo.http import request


class MagentoOnboarding(http.Controller):
    """
        Controller for Onboarding (Banner).
    """

    @http.route('/magento_instances/magento_instances_onboarding_panel', auth='user', type='json')
    def magento_instances_onboarding_panel(self):
        """ Returns the `banner` for the Magento onboarding panel.
            It can be empty if the user has closed it or if he doesn't have
            the permission to see it. """

        current_company_id = []
        if request.httprequest.cookies.get('cids'):
            current_company_id = request.httprequest.cookies.get('cids').split(',')
        company = False
        if len(current_company_id) > 0 and current_company_id[0] and \
                current_company_id[0].isdigit():
            company = request.env['res.company'].sudo().search(
                [('id', '=', int(current_company_id[0]))])
        if not company:
            company = request.env.company
        if not request.env.is_admin() or \
                company.magento_onboarding_state == 'closed':
            return {}
        hide_panel = company.magento_onboarding_toggle_state != 'open'
        btn_value = 'Create more Magento instance' if hide_panel else 'Hide On boarding Panel'
        panel_id = 'odoo_magento2_ept.magento_instances_onboarding_panel_ept'
        return {
            'html': request.env.ref(panel_id)._render({
                'company': company,
                'toggle_company_id': company.id,
                'hide_panel': hide_panel,
                'btn_value': btn_value,
                'state': company.get_and_update_magento_instances_onboarding_state(),
                'is_button_active': company.is_create_magento_more_instance
            })
        }
