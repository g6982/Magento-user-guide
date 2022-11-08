# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes flow to configure the notification instance wise
"""
from odoo import models, fields, api


class MagentoNotificationEpt(models.TransientModel):
    """
    Describes Magento Instance Configurations
    """
    _name = 'magento.notification.ept'
    _description = "To manage notifications and schedule activity"

    def _get_internal_user_domain(self):
        group_id = self.env.ref('base.group_user').id
        return [('groups_id', 'in', [group_id])]

    is_enable = fields.Boolean(string="Create Schedule Activity?")
    user_ids = fields.Many2many(comodel_name='res.users',
                                string="Responsible User",
                                help="Activity will be created for the selected user.",
                                domain=_get_internal_user_domain)
    activity_type = fields.Many2one(comodel_name='mail.activity.type',
                                    name="Activity Type",
                                    help="Select that which type of activity you want to create.")
    lead_days = fields.Integer(string="Deadline Lead Days",
                               help="Activity deadline days. \n "
                                    "-If you add 1 then it will create"
                                    "activity with deadline of tomorrow.")

    def set_notification(self):
        instance = self.env['magento.instance'].browse(self.env.context.get('active_id', 0))
        if instance:
            instance.write({
                'is_create_activity': True,
                'activity_type': self.activity_type.id,
                'activity_user_ids': [(6, 0, self.user_ids.ids)],
                'activity_lead_days': self.lead_days
            })
        return True

    @api.model
    def default_get(self, fields):
        result = super(MagentoNotificationEpt, self).default_get(fields)
        instance = self.env['magento.instance'].browse(self.env.context.get('active_id', 0))
        if instance:
            result.update({
                'is_enable': instance.is_create_activity,
                'user_ids': [(6, 0, instance.activity_user_ids.ids)],
                'activity_type': instance.activity_type.id,
                'lead_days': instance.activity_lead_days
            })
        return result
