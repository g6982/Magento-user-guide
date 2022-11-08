"""For Odoo Magento2 Connector Module"""
from odoo import models


class AccountTaxCode(models.Model):
    """Inherited account tax model to calculate tax."""
    _inherit = 'account.tax'

    def get_tax_from_rate(self, rate, name, is_tax_included=False, country=False):
        """
        This method,base on rate it find tax in odoo.
        @return : Tax_ids
        @author: Haresh Mori on dated 10-Dec-2018
        """
        for precision in [0.001, 0.01]:
            if country:
                tax_ids = self.with_context(active_test=False).search(
                    [('price_include', '=', is_tax_included),
                     ('type_tax_use', 'in', ['sale']),
                     ('amount', '>=', rate - precision),
                     ('amount', '<=', rate + precision),
                     ('country_id', '=', country.id)], limit=1)
                return tax_ids
            else:
                tax_ids = self.with_context(active_test=False).search(
                    [('price_include', '=', is_tax_included),
                     ('type_tax_use', 'in', ['sale']),
                     ('amount', '>=', rate - precision),
                     ('amount', '<=', rate + precision)], limit=1)
                return tax_ids
        return self
