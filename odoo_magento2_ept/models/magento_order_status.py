# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from .api_request import req

class MagentoOrderStatusEpt(models.Model):
    _name = "magento.order.status.ept"
    _description = 'Magento Order Status'

    main_status = fields.Selection([('pending', 'Pending'),
                                    ('processing', 'Processing'),
                                    ('complete', 'Complete'), ])
    m_order_status = fields.Char(string="Magento Orders",
                                 required=True, readonly=True,
                                 help="Magento Orders Status")

    m_order_status_code = fields.Char(string="Magento Orders Code", help="Magento Orders Code")
    magento_instance_id = fields.Many2one(comodel_name='magento.instance', string='Instance',
                                          ondelete="cascade",
                                          help="This field relocates magento instance")

    _sql_constraints = [('_magento_order_statue_map_unique_constraint',
                         'unique(main_status,magento_instance_id,m_order_status_code)',
                         "Financial status must be unique in the list")]

    def create_order_status(self, magento_instance):
        """
        Creates Financial Status for the payment methods of the Instance.
        :param magento_instance: Magento Instance
        :param financial_status: Financial Status can be pending, processing_paid, processing_unpaid or paid.
        :return: True
        """
        url = '/V1/orderstatus'
        magento_orderstatus = req(magento_instance, url)
        for status in magento_orderstatus:
            m_order_status_lbl = status.get('label', '')
            m_order_status_value = status.get('value', '')
            if m_order_status_value in ['canceled','closed']:
                continue
            domain = [('magento_instance_id', '=', magento_instance.id),
                                     ('m_order_status', '=', m_order_status_lbl),
                                     ('m_order_status_code', '=', m_order_status_value)]
            existing_order_status = self.search(domain).ids
            if existing_order_status:
                continue
            main_status = ''
            if m_order_status_value == 'pending':
                main_status = m_order_status_value
            if m_order_status_value == 'processing':
                main_status = m_order_status_value
            if m_order_status_value == 'complete':
                main_status = m_order_status_value
            self.create({
                     'magento_instance_id': magento_instance.id,
                     'main_status':main_status,
                     'm_order_status': m_order_status_lbl,
                     'm_order_status_code': m_order_status_value,
                 })
        return True
