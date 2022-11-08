# -*- coding: utf-8 -*-
"""
@author: Emipro Technologies Pvt. Ltd.
@create_date: 13.05.2021
"""

from odoo import models, fields, api


class MagentoExportCreditMemo(models.TransientModel):
    _name = "magento.export.credit.memo"
    _description = 'Magento Export Credit Memo'

    refund_type = fields.Selection([('online', 'Online'), ('offline', 'Offline')], default='online',
                                   string='Refund Type (Online/Offline)',
                                   help='If checked then refunded online,'
                                        'Other wise refunded offline')
    is_return_stock = fields.Boolean(string="Return items to Stock?",
                                     help="If true, System will return the refunded items to "
                                          "stock.")

    def export_credit_memo(self):
        """
        This method is used to create the credit memo request
        Task_id : 173739
        ----------------
        :return: True
        """
        credit_note = self.env['account.move'].browse(self._context.get('active_id'))
        credit_note.action_create_credit_memo(self.refund_type, self.is_return_stock)
        return True
