# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes configuration for Magento Instance.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResConfigMagentoInstance(models.TransientModel):
    """
    Describes configuration for Magento instance
    """
    _name = 'res.config.magento.instance'
    _description = 'Res Config Magento Instance'

    name = fields.Char("Instance Name")
    magento_version = fields.Selection([
        ('2.1', '2.1+'),
        ('2.2', '2.2+'),
        ('2.3', '2.3+')
    ], string="Magento Versions", required=True, help="Version of Magento Instance", default='2.2')
    magento_url = fields.Char(string='Magento URLs', required=True, help="URL of Magento")
    magento_admin_url = fields.Char(string='Magento Admin URL', required=True, help="URL of Magento Backend")
    access_token = fields.Char(
        string="Magento Access Token",
        help="Set Access token: Magento=>System=>Integrations"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Magento Company',
        help="Magento Company"
    )
    is_use_odoo_order_sequence = fields.Boolean(
        "Is Use Odoo Order Sequences?",
        default=False,
        help="If checked, Odoo Order Sequence is used"
    )
    is_multi_warehouse_in_magento = fields.Boolean(
        string="Is Multi Inventory Sources in Magento?",
        default=False,
        help="If checked, Multi Inventory Sources used in Magento"
    )
    magento_verify_ssl = fields.Boolean(
        string="Verify SSL", default=False,
        help="Check this if your Magento site is using SSL certificate")

    @api.onchange('magento_version')
    def _onchange_magento_version(self):
        if self.magento_version != '2.3':
            self.is_multi_warehouse_in_magento = False

    def create_magento_instance(self):
        """
        Creates Magento Instance.
        """
        magento_instance_obj = self.env['magento.instance']
        magento_url = self.magento_url.rstrip('/')
        magento_instance_exist = magento_instance_obj.with_context(active_test=False).search([
            ('magento_url', '=', magento_url)])
        if magento_instance_exist:
            raise UserError(_('The instance already exists for the given Hostname. '
                              'The Hostname must be unique, for instance. '
                              'Please check the existing instance; '
                              'if you cannot find the instance, '
                              'please check whether the instance is archived.'))
        vals = {
            'name': self.name,
            'access_token': self.access_token,
            'magento_version': self.magento_version,
            'magento_url': magento_url,
            'magento_admin_url': self.magento_admin_url,
            'company_id': self.company_id.id,
            'is_multi_warehouse_in_magento': self.is_multi_warehouse_in_magento,
            'magento_verify_ssl': self.magento_verify_ssl
        }
        magento_instance = magento_instance_obj
        magento_instance = magento_instance.create(vals)
        try:
            magento_instance and magento_instance.synchronize_metadata()
        except Exception as error:
            magento_instance.sudo().unlink()
            raise UserError(str(error))
        if self._context.get('is_calling_from_magento_onboarding_panel', False):
            company = magento_instance.company_id
            magento_instance.write({'is_instance_create_from_onboarding_panel': True})
            company.set_onboarding_step_done('magento_instance_onboarding_state')
            company.write({'is_create_magento_more_instance': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def download_magento_api_module(self):
        """
        This Method relocates download zip file of Magento API module.
        :return: This Method return file download file.
        """
        attachment = self.env['ir.attachment'].search(
            [('name', '=', 'emipro_magento_api_change.zip')])
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    @api.model
    def action_open_magento_instance_wizard(self):
        """ Called by onboarding panel above the Instance."""
        ir_action_obj = self.env["ir.actions.actions"]
        magento_instance_obj = self.env['magento.instance']
        action = ir_action_obj._for_xml_id(
            "odoo_magento2_ept.magento_on_board_instance_configuration_action")
        action['context'] = {'is_calling_from_magento_onboarding_panel': True}
        instance = magento_instance_obj.search_magento_instance()
        if instance:
            action.get('context').update({
                'default_name': instance.name,
                'default_magento_version': instance.magento_version,
                'default_access_token': instance.access_token,
                'default_company_id': instance.company_id.id,
                'default_magento_url': instance.magento_url,
                'default_is_multi_warehouse_in_magento': instance.is_multi_warehouse_in_magento,
                'default_magento_verify_ssl': instance.magento_verify_ssl,
                'is_already_instance_created': True,
                'is_calling_from_magento_onboarding_panel': False
            })
            company = instance.company_id
            if company.magento_instance_onboarding_state != 'done':
                company.set_onboarding_step_done('magento_instance_onboarding_state')
        return action
