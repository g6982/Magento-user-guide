from odoo import models, _


class MagentoOnboardingConfirmationEpt(models.TransientModel):
    _name = 'magento.onboarding.confirmation.ept'
    _description = 'Magento Onboarding Confirmation'

    def complete_configuration(self):
        """
        Save the Cron Changes by Instance Wise
        :return: True
        """
        magento_instance_obj = self.env['magento.instance']
        magento_instance_id = self._context.get('magento_instance_id', False)
        if magento_instance_id:
            magento_instance = magento_instance_obj.browse(magento_instance_id)
            company = magento_instance.company_id
            company.write({
                'magento_instance_onboarding_state': 'not_done',
                'magento_basic_configuration_onboarding_state': 'not_done',
                'magento_financial_status_onboarding_state': 'not_done',
                'magento_cron_configuration_onboarding_state': 'not_done',
                'is_create_magento_more_instance': False
            })
            magento_instance.write({'is_onboarding_configurations_done': True})
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': _("Congratulations, You have done All Configurations of Instance : {}").format(magento_instance.name),
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def not_complete_configuration(self):
        """
        Discard the changes and reload the page.
        :return: Reload the page
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
