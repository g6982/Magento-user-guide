# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
""" Usage : Inherit the model res company and added and manage the functionality of Onboarding Panel"""
from odoo import fields, models, api

MAGENTO_ONBOARDING_STATES = [
    ('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")]


class ResCompany(models.Model):
    """
    Inherit Class and added and manage the functionality of Onboarding (Banner) Panel
    """
    _inherit = 'res.company'

    # Magento Onboarding Panel
    magento_onboarding_state = fields.Selection(
        selection=MAGENTO_ONBOARDING_STATES, string="State of the Magento onboarding panel",
        default='not_done')
    magento_instance_onboarding_state = fields.Selection(
        selection=MAGENTO_ONBOARDING_STATES,
        string="State of the magneto instance onboarding panel", default='not_done')
    magento_basic_configuration_onboarding_state = fields.Selection(
        MAGENTO_ONBOARDING_STATES,
        string="State of the magento basic configuration onboarding step", default='not_done')
    magento_financial_status_onboarding_state = fields.Selection(
        MAGENTO_ONBOARDING_STATES,
        string="State of the onboarding magento financial status step", default='not_done')
    magento_cron_configuration_onboarding_state = fields.Selection(
        MAGENTO_ONBOARDING_STATES,
        string="State of the onboarding magento cron configurations step", default='not_done')
    is_create_magento_more_instance = fields.Boolean(string='Is create magento more instance?',
                                                     default=False)
    magento_onboarding_toggle_state = fields.Selection(
        selection=[('open', "Open"), ('closed', "Closed")], default='open')

    @api.model
    def action_close_magento_instances_onboarding_panel(self):
        """ Mark the onboarding panel as closed. """
        self.env.company.magento_onboarding_state = 'closed'

    def get_and_update_magento_instances_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = [
            'magento_instance_onboarding_state',
            'magento_basic_configuration_onboarding_state',
            'magento_financial_status_onboarding_state',
            'magento_cron_configuration_onboarding_state',
        ]
        return self.get_and_update_onbarding_state('magento_onboarding_state', steps)

    def action_toggle_magento_instances_onboarding_panel(self):
        """
        To change and pass the value of selection of current company to hide / show panel.
        :return Selection Value
        """
        self.magento_onboarding_toggle_state = 'closed' if self.magento_onboarding_toggle_state == 'open' else 'open'
        return self.magento_onboarding_toggle_state
