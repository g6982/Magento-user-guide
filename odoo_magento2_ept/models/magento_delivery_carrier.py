# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods and fields for Magento Delivery Carriers
"""
from odoo import models, fields, api


class MagentoDeliveryCarrier(models.Model):
    """
    Model for Magento's carriers.
    """
    _name = 'magento.delivery.carrier'
    _rec_name = 'carrier_code'
    _description = 'Magento Delivery Carrier'

    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string="Instance",
                                          help="This field relocates Magento Instance")
    delivery_carrier_ids = fields.One2many(comodel_name="delivery.carrier",
                                           inverse_name="magento_carrier",
                                           help="Delivery Methods for Magento")
    carrier_label = fields.Char(string="Label", help="Carrier Label")
    carrier_code = fields.Char(string="Code", help="Carrier Code")
    magento_carrier_title = fields.Char(string="Title", help="Carrier Title")

    _sql_constraints = [
        ('unique_magento_delivery_code', 'unique(magento_instance_id,carrier_code)',
         'This delivery carrier code is already exists')]

    @api.depends('carrier_code')
    def name_get(self):
        """
        Append the Magento instance name with Delivery Carrier code in the list only.
        :return:
        """
        result = []
        for delivery in self:
            instance_name = ' - ' + delivery.magento_instance_id.name if delivery.magento_instance_id else False
            name = "[" + delivery.carrier_label + "]  " + delivery.carrier_code + instance_name if instance_name else delivery.carrier_code
            result.append((delivery.id, name))
        return result
