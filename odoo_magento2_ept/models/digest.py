from odoo import models, fields


class Digest(models.Model):
    _inherit = 'digest.digest'

    magento_instance_id = fields.Many2one('magento.instance')

    def _prepare_domain_magento_digest(self):
        """
        Prepared magento instance domain for magento connector Digest.
        @author: Nikul Alagiya on Date 18-07-2022
        """
        domain = []
        domain += [('magento_instance_id', '=', self.magento_instance_id.id)]
        if self.kpi_orders:
            self.get_total_orders_count(domain)
        if self.kpi_refund_orders:
            self.get_refund_orders_count(domain)
        if self.kpi_avg_order_value:
            self.get_orders_average(domain)
        if self.kpi_cancel_orders:
            self.get_cancel_orders_count(domain)
        if self.kpi_account_total_revenue:
            self.get_account_total_revenue(domain)
        if self.kpi_late_deliveries:
            self.get_late_delivery_orders_count(domain)
        if self.kpi_on_shipping_orders:
            self.get_on_time_shipping_ratio(domain)
        if self.kpi_shipped_orders:
            domain.append(('is_exported_to_magento', '=', True))
            self.get_shipped_orders_count(domain)
        if self.kpi_pending_shipment_on_date:
            domain.pop(1)
            domain.append(('is_exported_to_magento', '=', False))
            self.get_pending_shipment_on_date_count(domain)
        return True

    def _prepare_domain_based_on_connector(self):
        if self.magento_instance_id:
            self._prepare_domain_magento_digest()
        return super(Digest, self)._prepare_domain_based_on_connector()
