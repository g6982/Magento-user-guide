# See LICENSE file for full copyright and licensing details.
"""
Describes methods and fields for Magento's Delivery Carriers
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    """
    Inherited for Magento's carriers.
    """
    _inherit = "delivery.carrier"

    magento_carrier = fields.Many2one(comodel_name='magento.delivery.carrier',
                                      help="This field relocates Magento Delivery Carrier",
                                      domain=[('magento_instance_id', '!=', False),
                                              ('magento_instance_id.active', '=', True)])
    magento_carrier_code = fields.Char(compute='_compute_carrier_code', string='Base Carrier Code',
                                       help="Magento Carrier Code")

    def _compute_carrier_code(self):
        for carrier in self:
            self.magento_carrier_code = False
            if carrier.magento_carrier.carrier_code:
                self.magento_carrier_code = carrier.magento_carrier.carrier_code

    @api.constrains('magento_carrier')
    def _check_magento_carrier_id(self):
        """
        User can only map one Magento carrier code with odoo's single Delivery Method per instance.
        :return:
        """
        delivery_carrier_obj = self.magento_carrier.delivery_carrier_ids. \
            filtered(lambda x: x.id != self.id)
        if delivery_carrier_obj:
            raise UserError(_("Can't set this same Magento carrier "
                              "with multiple Delivery Methods for the same Magento Instance"))

    def find_delivery_carrier(self, item, instance, log, line):
        carrier = self.env["delivery.carrier"]
        order_ref = item.get('increment_id')
        shipping = item.get('extension_attributes', {}).get('shipping_assignments', [])
        method = shipping[0].get('shipping', {}).get('method', False)
        if method:
            magento_carrier = self.__find_magento_carriers(instance, method)
            if not magento_carrier:
                message = _(f"""
                Order {order_ref} was skipped because when importing order the delivery 
                method {method} could not find in the Magento.
                """)
                log.write({'log_lines': [(0, 0, {
                    'message': message, 'order_ref': line.magento_id,
                    'magento_order_data_queue_line_id': line.id
                })]})
                return False
            if magento_carrier:
                carrier = carrier.search([('magento_carrier', '=', magento_carrier.id)], limit=1)
                if not carrier:
                    shipping_product = self.env.ref('odoo_magento2_ept.product_product_shipping')
                    product = instance.shipping_product_id or shipping_product
                    carrier_label = magento_carrier.carrier_label or magento_carrier.carrier_code
                    carrier.create({
                        'name': carrier_label,
                        'product_id': product.id,
                        'magento_carrier': magento_carrier.id
                    })
                item.update({
                    'magento_carrier_id': magento_carrier.id,
                    'delivery_carrier_id': carrier.id
                })
        return True

    def __find_magento_carriers(self, instance, shipping_method):
        carrier = self.env['magento.delivery.carrier']
        carrier = carrier.search([('carrier_code', '=', shipping_method),
                                  ('magento_instance_id', '=', instance.id)], limit=1)
        if not carrier:
            instance.import_delivery_method()
            carrier = carrier.search([('carrier_code', '=', shipping_method),
                                      ('magento_instance_id', '=', instance.id)], limit=1)
        return carrier
